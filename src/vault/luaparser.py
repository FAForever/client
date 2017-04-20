"""
lua data parser by Raging_Squirrel

to parse lua file, initialize the class with path to the file
call parse method to extract the data you need
the 1st parameter is a dictionary which represents search and data mapping
    keys: 'parent>name:command' - where to search
    values: 'destination:alias' - how to map found data in the result
the 2nd parameter is a dictionary of default values
    keys: resulting item name (same as value of search dict)
    value: default value for not found item

*** IMPORTANT ***
All the parsed lua item names are lower case (not the values)
If there were more than one occurrences found, only the last matched is returned
If there is default value for a search entry, error will not be generated. Default value will be returned instead
*** IMPORTANT ***

    'parent>name:command'
    you can use * character here
    parent - item parent
        you can specify multiple parents (parent1>parent2>...>name)
        you should explicitly specify parents (you cannot drop in-between parents and expect it will find desired items)
        you can drop parents at all
    name - name of desired parameter in lua in lower case
        special characters, like ' [ ] " are pulled down
    command - an instruction to the parser (only 1 supported command so far)
        count - counts all matched elements if they are strings, and size of lists or dicts otherwise
        
    'destination:alias'
    alias - a name under which matched item will be returned
        you can use any of following patterns:
        __self__ - returns item name as it is in lua
        __parent__ - returns item parent
    destination - you can specify a dictionary for matched items in the resulting array
"""
import re
import zipfile
import os

class luaParser:
    
    def __init__(self, luaPath):
        self.iszip = False
        self.zip = None
        self.__path = luaPath
        self.__keyFilter = re.compile("[\[\],'\"]")
        self.__valFilter = re.compile("[\[\]]")
        self.__searchResult = dict()
        self.__searchPattern = dict()
        self.__foundItemsCount = dict()
        self.__stream = list()
        self.__lines = list()
        self.__prevUnfinished = False
        self.__inString = False
        self.__stringChar = ""
        self.__parsedData = dict()
        self.__defaultValues = dict()
        self.errors = 0
        self.warnings = 0
        self.error = False
        self.warning = False
        self.errorMsg = ""
        self.loweringKeys = True
    
    def __checkUninterruptibleStr(self, char):
        if char == "\"" or char == "'":
            if not self.__inString:
                self.__stringChar = char
                self.__inString = True
            elif char == self.__stringChar:
                self.__inString = False
        elif not self.__inString and char == "(":
            self.__inString = True
            self.__stringChar = ")"
    
    def __processLine(self, parent=""):
        #initialize item counter
        counter = 0
        #initialize empty array
        lua = dict()
        #initialize value
        value = ""
        #start cycle
        while len(self.__stream):
            #get a line from the list or read next line from the file
            if len(self.__lines) == 0:
                line = self.__stream.pop(0)
                #cut commentary section (either start whit '#' or is a '--[[  ]]--' section
                comment = re.compile("((#.*))$|((--\[\[).*(\]\]--)$)")
                line = comment.sub("", line)
                #process line to see if it one command or a stack of them
                newLine = 0
                pos = 0
                self.__inString = False
                while len(line) > pos:
                    char = line[pos]
                    self.__checkUninterruptibleStr(char)
                    if char == "{":
                        pos = pos + 1
                        char = line[pos]
                        self.__checkUninterruptibleStr(char)
                        self.__lines.append(line[newLine:pos])
                        newLine = pos
                    elif char == ","  and not self.__inString:
                        self.__lines.append(line[newLine:pos])
                        pos = pos + 1
                        char = line[pos]
                        self.__checkUninterruptibleStr(char)
                        newLine = pos
                    elif char == "}":
                        self.__lines.append(line[newLine:pos])
                        self.__lines.append("}")
                        pos = pos + 1
                        if pos <= len(line):
                            self.__checkUninterruptibleStr(line[pos])
                        newLine = pos
                    pos = pos + 1
                if len(self.__lines) > 0:
                    line = self.__lines.pop(0)
            else:
                line = self.__lines.pop(0)
            line = line.strip()
            #if the string is not empty, proceed
            if line != "":
                #split it by '='
                lineArray = line.split("=")
                #if result is one element list
                if len(lineArray) == 1:
                    #this element is value
                    value = lineArray[0].strip()
                    #assign counter value to key
                    key = str(counter)
                else:
                    #first is key
                    if self.loweringKeys:
                        key = lineArray[0].lower()
                    else:
                        key = lineArray[0]
                    #get rid of redundant chars in key
                    key = self.__keyFilter.sub("", key).strip()
                    #second is value
                    value = lineArray[1].strip()
                #if value is '}' - which is end of lua array, stop parsing
                if value == "}":
                    break
                unfinished = False
                if len(value) != 0:
                    #remove finishing comma if there is one
                    if value[-1] == ",":
                        value = value[:-1]
                    #get rid of redundant chars in value
                    value = self.__valFilter.sub("", value)
                if len(value) != 0:
                    #parse value:
                    #if the string starts with '{'
                    if value[-1] == "{":
                        #add new item into the array: recursive function call
                        if self.__prevUnfinished:
                            self.__prevUnfinished = False
                            lua[prevkey] = self.__processLine(parent+">"+prevkey)
                        else:
                            lua[key] = self.__processLine(parent+">"+key)
                    else:
                        #add new item into the array: value itself
                        if value[0] == "\"" or value[0] == "'":
                            value = value[1:]
                        if value[-1] == "\"" or value[-1] == "'":
                            value = value[:-1]
                        lua[key] = value
                elif len(value) != 0:
                    #add new item into the array: value itself
                    lua[key] = value
                elif len(key) != 0:
                    self.__prevUnfinished = True
                    prevkey = key
            #checking line if it suits searchPattern, and adding if so
                for searchKey in self.__searchPattern:
                    #regkey = re.compile(".*("+searchKey.split(":")[-1].replace("*", ".*")+")$")
                    #if regkey.match(parent+">"+key):
                    if re.match(".*>("+searchKey.split(":")[-1].replace("*", ".*")+")$", parent+">"+key):
                        #get command from key
                        valcmd = searchKey.split(":")
                        valcmd = valcmd[0] if len(valcmd) == 2 else "none"
                        #add new value into the resulting array
                        resultKey = self.__searchPattern[searchKey]
                        if valcmd == "count":
                            if key in lua:
                                if isinstance(lua[key], str):
                                    count = 1
                                else:
                                    count = len(lua[key])
                            else:
                                count = 0
                            if resultKey in self.__searchResult:
                                resultVal = self.__searchResult[resultKey] + count
                            else:
                                resultVal = count
                        else:
                            resultVal = lua[key]
                        resultKey = resultKey.replace("__self__", key)
                        resultKey = resultKey.replace("__parent__", parent.split(">")[-1])
                        keycmd = resultKey.split(":")
                        #unpack command from search key
                        if len(keycmd) == 2:
                            resultKey = keycmd[1]
                            keydst = keycmd[0]
                        else:
                            keydst = "__nowhere__"
                        #write result into the array
                        if keydst == "__nowhere__":
                            self.__searchResult[resultKey] = resultVal
                        else:
                            if keydst in self.__searchResult:
                                if isinstance(self.__searchResult[keydst], dict):
                                    self.__searchResult[keydst][resultKey] = resultVal
                            else:
                                self.__searchResult[keydst] = dict()
                                self.__searchResult[keydst][resultKey] = resultVal
                        if isinstance(resultVal, int):
                            self.__foundItemsCount[searchKey] = self.__foundItemsCount[searchKey] + resultVal
                        else:
                            self.__foundItemsCount[searchKey] = self.__foundItemsCount[searchKey] + 1
            #increase counter
            counter = counter + 1
        #return resulting array
        return lua
        
    def __parseLua(self):
        #open file
        if self.iszip == False:
            f = open(self.__path, "r")
        else:
            if self.zip.testzip() == None :
                for member in self.zip.namelist() :
                    filename = os.path.basename(member)
                    if not filename:
                        continue
                    if filename == self.__path:
                        f = self.zip.open(member)
                        break
        if not f :
            return
            

        self.__stream = f.readlines()
        if self.__stream[-1][-1] != "\n": # file doesn't end in a newline
                        self.__stream[-1] += "\n" # needed to prevent a bug happening when a file doesn't end with a newline.
        f.close()
        #call recursive function
        result = self.__processLine()
        return result
    
    def __checkErrors(self):
        for key in self.__foundItemsCount:
            resultKey = self.__searchPattern[key]
            if len(key.split(":")) == 2 or key.find("*") != -1:
                if self.__foundItemsCount[key] == 0:
                    if resultKey in self.__defaultValues:
                        self.__searchResult[resultKey] = self.__defaultValues[resultKey]
                    else:
                        self.error = True
                        self.errors = self.errors + 1
                        self.errorMsg = self.errorMsg + "Error: no matches for '" + key + "' were found\n"
            else:
                if self.__foundItemsCount[key] == 0:
                    if resultKey in self.__defaultValues:
                        self.__searchResult[resultKey] = self.__defaultValues[resultKey]
                    else:
                        self.error = True
                        self.errors = self.errors + 1
                        self.errorMsg = self.errorMsg + "Error: no matches for '" + key + "' were found\n"
                elif self.__foundItemsCount[key] > 1:
                    self.warning = True
                    self.warnings = self.warnings + 1
                    self.errorMsg = self.errorMsg + "Warning: there were duplicate occurrences for '" + key + "'\n"
                    
    def parse(self, luaSearch, defValues = dict()):
        self.__searchPattern.update(luaSearch)
        self.__defaultValues.update(defValues)
        self.__foundItemsCount = {}.fromkeys(list(self.__searchPattern.keys()), 0)
        self.__parsedData = self.__parseLua()
        self.__checkErrors()
        return self.__searchResult
