import regex as re
from typing import List
from collections import OrderedDict

class EuphonyError(Exception):
    pass

class Parser:
    def read_file(self, file_name: str) -> None:
        for line in open(file_name, "r").readlines():
            if line == "\n" or line.startswith("--"):
                continue
            self.parse_line(line)
            
    def parse_line(self, line: str) -> None:
        raise EuphonyError("Undefined")

class Category:
    def __init__(self, name: str, arr: List[str]) -> None:
        self.name = name
        self.arr = arr
    
    def to_regex(self) -> str:
        enclosed = list(map(lambda s: "(?:{})".format(s), self.arr))
        return "(?:{})".format("|".join(enclosed))
    
    def __repr__(self) -> str:
        return "Category(name={}, arr={})".format(self.name, self.arr)
        
class Categories:
    def __init__(self) -> None:
        self.cats = OrderedDict()
        
    def _to_array(self, phrase: str) -> str:
        return phrase.split(" ")
        
    def add_category(self, name: str, expanded: str) -> str:
        self.cats[name] = Category(name, self._to_array(expanded))
        
    def get_nonce_categories(self, phrase: str) -> List[Category]:
        return [
            Category("[{}]".format(nonce_category), self._to_array(nonce_category))
            for nonce_category in re.findall("\[(.*?)\]", phrase)]
            
    def expand_cats(self, phrase: str) -> str:
        expanded = phrase
        if expanded[0] == "#":
            expanded = "^" + expanded[1:]
        if expanded[-1] == "#":
            expanded = expanded[:-1] + "$"
        expanded = expanded.replace("(", "(?:") # do not capture anything
        expanded = expanded.replace(")", ")?") # sound change (...) is actually regex optional
        for cat in reversed(self.cats.values()):
            expanded = expanded.replace(cat.name, cat.to_regex())
        for cat in self.get_nonce_categories(phrase):
            expanded = expanded.replace(cat.name, cat.to_regex())
        return expanded
    
    def get_cat(self, phrase: str) -> Category:
        a = [self.cats[cat] for cat in self.cats if cat in phrase] + self.get_nonce_categories(phrase)
        if len(a) > 1:
            raise EuphonyError("Too many categories in phrase \"{}\"!".format(phrase))
        elif a:
            return a[0]
        else:
            return None
        
class Environments:
    def __init__(self) -> None:
        self.envs = {}
        
    def add_env(self, name: str, expanded: str) -> None:
        self.envs[name] = expanded
        
    def expand(self, phrase: str) -> str:
        expanded = phrase
        for env in self.envs:
            expanded = expanded.replace(env, self.envs[env])
        return expanded
    
class Rule:
    def __init__(self, fr: str, to: str, cond: str) -> None:
        self.fr = fr
        self.to = to
        self.cond = cond
        
    def apply(self, word: str) -> str:
        if self.to == "_": # deletion
            self.to = ""
        if self.fr == "_": # excrescence
            pattern = r'(?<=' + self.cond.replace("_", ")(?=") + r')'
            repl = self.to
        else:
            pattern = r'(?<=' + self.cond.replace("_", ")({})(?=".format(self.fr)) + r')'
            repl = self.to
        return re.sub(pattern, repl, word)
        
    def __repr__(self) -> str:
        return "Rule({} > {} / {})".format(self.fr, self.to, self.cond)
            
class Rules(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.rules: List[Rule] = []
        self.cat = Categories()
        self.envs = Environments()
        
    def apply_all(self, word: str) -> List[str]:
        stages = [word]
        for rule in self.rules:
            if rule == "!":
                stages.append(word)
            elif type(rule) == list:
                tos = []
                for i, sim_rule in enumerate(rule):
                    tos.append(sim_rule.to)
                    sim_rule.to = "${0:03d}".format(i)
                    word = sim_rule.apply(word)
                for i, to in enumerate(tos):
                    rule[i].to = to
                    word = word.replace("${0:03d}".format(i), to)
            else:
                word = rule.apply(word)
        stages.append(word)
        return stages
    
    def parse_simple_rule(self, fr: str, to: str, cond: str) -> None:
        fr = self.cat.expand_cats(fr)
        cond = self.envs.expand(cond)
        cond = self.cat.expand_cats(cond)
        return Rule(fr, to, cond)
        
    def parse_rule(self, fr: str, to: str, cond: str) -> None:
        to_cat = self.cat.get_cat(to)
        if to_cat:
            fr_cat = self.cat.get_cat(fr)
            if not fr_cat or len(fr_cat.arr) != len(to_cat.arr):
                raise EuphonyError("Cannot match category {} to {}!".format(fr_cat, to_cat))
            sim = []
            for i in range(len(fr_cat.arr)):
                sim.append(self.parse_simple_rule(fr.replace(fr_cat.name, fr_cat.arr[i]), to.replace(to_cat.name, to_cat.arr[i]), cond))
            self.rules.append(sim)
        else:
            self.rules.append(self.parse_simple_rule(fr, to, cond))
    
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
        
            
class Word:
    def __init__(self, word: str, gloss: str) -> None:
        self.word = word
        self.gloss = gloss
                      
class Words(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.words: List[Word] = []
        
    def parse_line(self, line: str) -> None:
        word, gloss = re.match("([^\s]*)(?:\s*\"([^\s*]*)\")?", line).group(1, 2)
        if not gloss:
            gloss = ""
        self.words.append(Word(word, gloss))
        
r = Rules()
r.read_file("input_rules.txt")
w = Words()
w.read_file("input_wordlist.txt")

for word in w.words:
    print(" -> ".join(r.apply_all(word.word)))