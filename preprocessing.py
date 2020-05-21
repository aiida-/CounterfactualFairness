import os
import pandas as pd
from tqdm import tqdm
from helpers import read_sgts
import re
import torch


class Preprocessing():

    def __init__(self, predict_dir, sgt_path, result_dir):
        self.predict_dir = predict_dir
        self.sgt_file_path = sgt_path
        with open(sgt_path) as f:
            content = f.readlines()
            self.sgts = [item.replace("\n", "") for item in content]
        self.result_dir = result_dir
        self.tokenizer = torch.hub.load('huggingface/pytorch-transformers', 'tokenizer', 'gpt2')
        self.model = torch.hub.load('huggingface/pytorch-transformers', 'modelWithLMHead', 'gpt2')
        self.found_sgts = []

    def extract_posts_with_sgt(self):

        for filename in os.listdir(self.predict_dir):
            print("--------------------------------")
            print(os.path.join(self.predict_dir, filename))
            print("--------------------------------")

            dataset = pd.read_csv(os.path.join(self.predict_dir, filename))
            rows_list = []
            for index, row in tqdm(dataset.iterrows()):
                text = row.text.lower()
                for sgt in self.sgts:
                     if re.findall("((^|[^\w])(" + sgt + ")([^\w]|$|s))", text):
                    #if sgt in text:
                        row_dict = dict(row)
                        row_dict["detected_sgt"] = sgt
                        rows_list.append(row_dict)
                        break
            sgt_data_df = pd.DataFrame(rows_list)
            result_path = os.path.join(self.result_dir, "SGT_" + filename)
            print("saving to", result_path)
            sgt_data_df.to_csv(result_path)

    def extract_all_sgts(self):
        for filename in os.listdir(self.result_dir):
            if not filename.startswith("SGT_"):
                continue
            print("--------------------------------")
            print(os.path.join(self.result_dir, filename))
            print("--------------------------------")
            dataset = pd.read_csv(os.path.join(self.result_dir, filename))
            rows_list = []
            for index, row in tqdm(dataset.iterrows()):
                text = row.text.lower()
                present_sgts = [sgt for sgt in self.sgts if
                                re.findall("((^|[^\w])(" + sgt + ")([^\w]|$|s))", text)]

                for sgt in present_sgts:
                    if sgt not in self.found_sgts:
                        self.found_sgts.append(sgt)

                present_sgts_str = ','.join(present_sgts)
                row_dict = dict(row)
                row_dict["sgts"] = present_sgts_str
                rows_list.append(row_dict)

            sgt_data_df = pd.DataFrame(rows_list)
            result_path = os.path.join(self.result_dir, "Populated_" + filename)
            print("saving to", result_path)
            sgt_data_df.to_csv(result_path)


    def merge_preprocessed_chunks(directory):
        os.chdir(directory)
        all_filenames = [i for i in os.listdir()]
        combined_csv = pd.concat([pd.read_csv(f) for f in all_filenames])
        combined_csv.to_csv("SGT-Gab.csv", index=False, encoding='utf-8-sig')


    def get_perplexity(self, text):
        token_ids = self.tokenizer.encode(text, add_special_tokens=True)
        input_ids = torch.tensor(token_ids).unsqueeze(0)  # Batch size 1
        outputs = self.model(input_ids)
        last_hidden_states = outputs[0]  # The last hidden-state is the first element of the output tuple
        perplexity = 0
        for i in range(len(token_ids)):
            index = token_ids[i]
            probs = torch.nn.functional.softmax(last_hidden_states[0, i, :], dim=0)
            prob = probs[index]
            perplexity += torch.log(prob.data)

        return perplexity

    def generate_counterfactuals(self, filename):
        pass