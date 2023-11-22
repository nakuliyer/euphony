import regex as re
from typing import List
from collections import OrderedDict
from e_types import *
from e_errors import *

class Parser:
    def read_file(self, file_name: str) -> None:
        for line in open(file_name, "r").readlines():
            if line == "\n" or line.startswith("--"):
                continue
            self.parse_line(line)
            
    def parse_line(self, line: str) -> None:
        raise EuphonyError("Undefined")
            
class Rules(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.rules: List[List[Rule]] = []
        self.cat = Categories()
        self.envs = Environments()
        
    def apply_all(self, word: Word) -> List[str]:
        stages = [word.opts]
        for rule in self.rules:
            if rule == "!":
                stages.append(word.opts)
            else:
                new_opts = set()
                for sub_rule in rule:
                    for opt in word.opts:
                        new_opts.add(sub_rule.apply(opt))
                word.opts = new_opts
        stages.append(word.opts)
        return stages
    
    def apply_all_and_display(self, word: Word) -> List[str]:
        stages = self.apply_all(word)
        str_stages = []
        for stage in stages:
            str_stages.append(", ".join(stage))
        # TODO: show glosses here
        return " -> ".join(str_stages)
    
    def parse_simple_rule(self, fr: str, to: str, cond: str) -> None:
        fr = self.cat.expand_cats(fr)
        cond = self.envs.expand(cond)
        cond = self.cat.expand_cats(cond)
        return SimpleRule(fr, to, cond)
        
    def parse_rule(self, fr: str, to: str, cond: str) -> None:
        for fr in re.split("\s*,\s*", fr):
            for cond in re.split("\s*,\s*", cond):
                tos = re.split("\s*,\s*", to)
                rules = []
                for to in tos:
                    to_cat = self.cat.get_cat(to)
                    if to_cat:
                        fr_cat = self.cat.get_cat(fr)
                        if not fr_cat or len(fr_cat.arr) != len(to_cat.arr):
                            raise EuphonyError("Cannot match category {} to {}!".format(fr_cat, to_cat))
                        sim = []
                        for i in range(len(fr_cat.arr)):
                            sim.append(self.parse_simple_rule(fr.replace(fr_cat.name, fr_cat.arr[i]), to.replace(to_cat.name, to_cat.arr[i]), cond))
                        rules.append(Rule(rules=sim))
                    else:
                        rules.append(Rule(rules=[self.parse_simple_rule(fr, to, cond)]))
                self.rules.append(rules)
    
    def parse_line(self, line: str) -> None:
        if line[0] == "!":
            self.rules.append("!")
            return
        i = line.find("--")
        if i != -1:
            line = line[:i - 1] # remove comments
        rule_line = re.match("(.*?)\s*\/\s*(.*?)\s*\/\s*(.*)$", line)
        cat_line = re.match("(.*?)\s*=\s*\[(.*?)\]\s*$", line)
        env_line = re.match("(.*?)\s*=\s*(.*)$", line)
        if rule_line:
            fr, to, cond = rule_line.group(1, 2, 3)
            cond = cond.strip()
            self.parse_rule(fr, to, cond)
        elif cat_line:
            cat, expanded = cat_line.group(1, 2)
            expanded = expanded.strip()
            self.cat.add_category(cat, expanded)
        elif env_line:
            env, expanded = env_line.group(1, 2)
            expanded = expanded.strip()
            self.envs.add_env(env, expanded)
                      
class Words(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.words: List[Word] = []
        
    def parse_line(self, line: str) -> None:
        word, gloss = re.match("([^\s]*)(?:\s*\"([^\s*]*)\")?", line).group(1, 2)
        if not gloss:
            gloss = ""
        self.words.append(Word(word, gloss))
        
    def apply_all_and_display(self, rules: Rules) -> None:
        # TODO: loop over words
        pass
        
        
r = Rules()
r.read_file("input_rules.txt")
w = Words()
w.read_file("input_wordlist.txt")

for word in w.words:
    print(r.apply_all_and_display(word))