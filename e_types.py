
import regex as re
from typing import List
from collections import OrderedDict
from e_errors import *

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
    
class SimpleRule:
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
    
class Rule:
    def __init__(self, 
                 rules: List[SimpleRule] = None):
        self.rules = rules
        self.type = type
        
    def apply(self, word: str) -> str:
        if len(self.rules) > 1:
            tos = []
            for i, sim_rule in enumerate(self.rules):
                tos.append(sim_rule.to)
                sim_rule.to = "${0:03d}".format(i)
                word = sim_rule.apply(word)
            for i, to in enumerate(tos):
                self.rules[i].to = to
                word = word.replace("${0:03d}".format(i), to)
            return word
        else:
            return self.rules[0].apply(word)
    
class Word:
    def __init__(self, word: str, gloss: str) -> None:
        self.word = word
        self.gloss = gloss
        self.opts = set([word])
