## Copyright 2002 by PyMMLib Development Group (see AUTHORS file)
## This code is part of the PyMMLib distrobution and governed by
## its license.  Please see the LICENSE file that should have been
## included as part of this package.

"""This module provides a primitive mmCIF file parser.  Files are parsed
into a set of data structures where they can be further processed.  The
data structures can also be constructed and written back out as mmCIF.
A CIF dictionary parser is also included as a specialized version of the
mmCIF parser."""

from   __future__           import generators
import string
import types

from   FileIO               import OpenFile
from   mmTypes              import *

##
## DATA STRUCTURES FOR HOLDING CIF INFORMATION
##
## mmCIF files are parsed into:
##         mmCIFFile -> [mmCIFData] -> [mmCIFTable] -> [mmCIFRow]
##
## mmCIF dictionaries are parsed into:
##         mmCIFDictionary -> [mmCIFData] -> [mmCIFTable] -> [mmCIFRow]
##

mmCIFError = "mmCIFError"


class mmCIFRow(dict):
    """Contains one row of data.  In a mmCIF file, this is one complete
    set of data found under a section.  The data can be accessed by using
    the column names as class attributes."""
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError, attr

    def __setattr__(self, attr, val):
        self[attr] = val
        

class mmCIFTable(object):
    """Contains columns and rows of data for a mmCIF section.  Rows of data
    are stored as mmCIFRow classes."""

    def __init__(self, name, columns = None):
        self.name       = name
        self.columns    = columns or []
        self.__row_list = []

    def __len__(self):
        return len(self.__row_list)

    def __getitem__(self, x):
        if type(x) == IntType:
            return self.__row_list[x]

        elif type(x) == StringType and len(self) == 1:
            return self.__row_list[0][x]

        raise TypeError, x

    def __delitem__(self, x):
        self.__row_list(self[x])

    def __iter__(self):
        return iter(self.__row_list)

    def append(self, row):
        assert isinstance(row, mmCIFRow)
        self.__row_list.append(row)

    def index(self, row):
        assert isinstance(row, mmCIFRow)
        return self.__row_list.index(row)

    def addColumn(self, cname):
        """Adds a column to the table.  In this case, a column is a
        mmCIF subsection."""
        self.columns.append(cname)
        
    def columnIndex(self, cname):
        """Returns the column index of from the column name."""
        return self.columns.index(cname)

    def getColumnList(self):
        """Returns a list of all column names, in order."""
        return self.columns

    def addRow(self, row):
        """Adds a mmCIFRow to the table."""
        assert isinstance(row, mmCIFRow)
        self.append(row)

    def getOneRow(self):
        """Some tables are defined to have only one row.  Return it or
        raise an error."""
        if len(self._row_list) != 1:
            raise mmCIFError, "table=%s has num_rows=%d" % (
                self._name, len(self._row_list))
        return self._row_list[0]

    def getRowList(self):
        """Returns a list of all mmCIFRow classes contained in the table."""
        return self.__row_list

    def selectRowList(self, *nvlist):
        """Preforms a SQL-like 'AND' select aginst all the rows in the table.
        The arguments are a variable list of tuples of the form:
          (<column-name>, <column-value>)
        For example:
          selectRowList(('atom_id','CA'),('entity_id', '1'))
        returns a list of rows with atom_id==1 and entity_id==1."""
        ## clever optimization tricks
        (attr, val) = nvlist[0]
        
        row_list = []
        for row in self:
            if row[attr] != val: continue
            
            add = 1
            for (attr, val) in nvlist:
                if row[attr] != val:
                    add = 0
                    break

            if add: row_list.append(row)

        return row_list

    def debug(self):
        print "mmCIFTable::%s" % (self._name)
        for row in self:
            for col in self.columns:
                print "%s=%s" % (col, getattr(row, col))[:80]
            print "---"


class mmCIFData(object):
    """Contains all information found under a data_ block in a mmCIF file.
    mmCIF files are represented differently here than their file format
    would suggest.  Since a mmCIF file is more-or-less a SQL database dump,
    the files are represented here with their sections as "Tables" and
    their subsections as "Columns".  The data is stored in "Rows"."""
    def __init__(self, name):
        self._name          = name
        self.__ctable_list  = []

    def __len__(self):
        return len(self.__ctable_list)

    def __getitem__(self, x):
        if type(x) == IntType:
            return self.__ctable_list[x]

        elif type(x) == StringType:
            for ctable in self.__ctable_list:
                if ctable.name == x:
                    return ctable
            raise KeyError, x

        raise TypeError, x

    def __delitem__(self, x):
        self.__ctable_list.remove(self[x])

    def __iter__(self):
        return iter(self.__ctable_list)

    def has_key(self, x):
        for ctable in self.__ctable_list:
            if ctable.name == x:
                return True
        return False

    def get(self, x, default = None):
        try:
            return self[x]
        except KeyError:
            return default

    def getName(self):
        """Returns the name given to the data section in the mmCIF file."""
        return self._name

    def addTable(self, ctable):
        """Adds a mmCIFTable class."""
        assert isinstance(ctable, mmCIFTable)
        
        self.__ctable_list.append(ctable)
        setattr(self, ctable.name, ctable)

    def getTable(self, name):
        """Looks up and returns a stored mmCIFTable class by it's name.  This
        name is the section key in the mmCIF file."""
        try:
            return self[name]
        except KeyError:
            return None
        except IndexError:
            return None

    def debug(self):
        print "mmCIFData::%s" % (self._name)
        for ctable in self:
            ctable.debug()


class mmCIFFile:
    """Class representing a mmCIF files."""
    def __init__(self):
        self.__cdata_list = []

    def __len__(self):
        return len(self.__cdata_list)

    def __getitem__(self, x):
        if type(x) == IntType:
            return self.__cdata_list[x]

        elif type(x) == StringType:
            for cdata in self.__cdata_list:
                if cdata._name == x:
                    return cdata
            raise KeyError, x

        raise TypeError, x

    def __delitem__(self, x):
        self.__cdata_list.remove(self[x])

    def __iter__(self):
        return iter(self.__cdata_list)

    def append(self, cdata):
        assert isinstance(cdata, mmCIFData)
        self.__cdata_list.append(cdata)
        setattr(self, cdata._name, cdata)

    def loadFile(self, fil):
        fil = OpenFile(fil, "r")
        for cif_data in mmCIFFileParser().parseFile(fil):
            self.addData(cif_data)

    def saveFile(self, fil):
        fil = OpenFile(fil, "w")
        mmCIFFileWriter().writeFile(fil, self.__cdata_list)

    def addData(self, cdata):
        self.append(cdata)

    def getData(self, name):
        try:
            return self[name]
        except KeyError:
            return None
        except IndexError:
            return None

    def debug(self):
        print "mmCIFFile"
        for cdata in self:
            cdata.debug()


class mmCIFDictionary(mmCIFFile):
    """Class representing a mmCIF dictionary.  The constructor of this class
    takes two arguments.  The first is the string path for the file, or
    alternativly a file object."""

    def __init__(self, path_or_fil):
        self._path = path_or_fil
        self._data_list = []


    def load(self):
        if type(self._path) == types.StringType:
            fil = OpenFile(self._path, "r")
        else:
            fil = self._path

        for cif_data in mmCIFDictionaryParser().parseFile(fil):
            self.addData(cif_data)



##
## FILE PARSERS/WRITERS
##

## charactors considered quotes
QUOTES = ["'", '"']

## maximum line width
MAX_LINE = 80



class mmCIFElementFile:
    """Tokenizes a mmCIF file for the state parser."""
    def __init__(self, file):
        self.file = file
        self.line_number = 0
        self.elements = []

    def escaped(self, line, i):
        """Given a line and a charactor index, determine if the charactor
        at index i is escaped."""
        j = i - 1
        while 1:
            try:
                if line[j] != "\\": break
            except IndexError:
                break
            j -= 1
        return not ((i - j) % 2)

    def split(self, line):
        list = []
        j = 0
        state = "whitespace"

        for i in range(len(line)):
            if state == "whitespace":
                if line[i] not in string.whitespace:
                    j = i
                    if line[i] in QUOTES:
                        state = "quote"
                    else:
                        state = "element"
                continue

            elif state == "element":
                if line[i] in string.whitespace:
                    state = "whitespace"
                    list.append((line[j:i], "token"))
                continue

            elif state == "quote":
                if line[i] in QUOTES:
                    try:
                        if line[i+1] not in string.whitespace: continue
                    except IndexError:
                        pass
                    
                    state = "whitespace"
                    list.append((line[j+1:i],"string")) ## strip quotes
                continue

        if  state == "element":
            list.append((line[j:],"token"))

        elif state == "quote":
            list.append((line[j+1:-1],"string")) ## strip out the quotes
            
        return list
 
    def read_elements(self):
        state = "read data"
        temp = ""
        
        while 1:
            line = self.file.readline()
            self.line_number += 1
            if not line:
                raise EOFError, "mmCIFElementFile"

            if state == "read data":
                if line[0] == '#':
                    continue
                if line[0] == ';':
                    state = "read ;string"
                    temp = line[1:]
                    continue
                elements = self.split(line)
                if elements:
                    self.elements += elements
                    break
                continue

            if state == "read ;string":
                if line[0] == ';':
                    state = "read data"
                    self.elements.append((temp.rstrip(), "string"))
                    break
                temp += line
                continue
        
    def getNextElement(self):
        if not self.elements:
            self.read_elements()
        return self.elements.pop(0)

    def peekNextElement(self):
        if not self.elements:
            self.read_elements()
        return self.elements[0]

    def replaceElement(self, element):
        self.elements.insert(0, element)



class mmCIFFileParser:
    """Stateful parser which uses the mmCIFElementFile tokenizer to read
    a mmCIF file and convert it into the mmCIFData/mmCIFTable/mmCIFRow
    data hierarchy."""

    error = "mmCIF Syntax Error"

    def syntax_error(self, err):
        err = "[line %d] %s" % (self.cife.line_number, err)
        raise self.error, err

    def parseFile(self, fil):
        self.done = 0
        self.cife = mmCIFElementFile(fil)

        data_list = []
        while not self.done:
            try:
                (s,t) = self.cife.getNextElement()
            except EOFError:
                self.done = 1
                break

            if s[:5] == 'data_':
                data = mmCIFData(s[5:])
                data_list.append(data)
                self.read_data(data)
            else:
                self.syntax_error('unexpected element=%s' % (s))

        return data_list

    def read_data(self, data):
        while not self.done:
            try:
                (s,t) = self.cife.getNextElement()
            except EOFError:
                self.done = 1
                break

            if s[0] == '_':
                self.read_single(data, s)
                
            elif s[:5] == 'loop_':
                self.read_loop(data, s)

            elif s[:5] == 'data_':
                self.cife.replaceElement((s,t))
                break

            else:
                self.syntax_error('bad element=%s' % (s))

    def read_single(self, data, s):
        (tname, cname) = s[1:].split(".")

        table = data.getTable(tname)
        if not table:
            table = mmCIFTable(tname)
            data.addTable(table)
            table.append(mmCIFRow())
        else:
            if cname in table.getColumnList():
                self.syntax_error('redefined single column %s.%s' % (
                    tname, cname))

        table.addColumn(cname)
        row = table[0]

        try:
            (s,t) = self.cife.getNextElement()
        except EOFError:
            self.syntax_error('premature end of file')

        if t == "token" and s[0] == '_':
            self.syntax_error('expected data got section=%s' % (s))

        row[cname] = s

    def read_loop(self, data, s):
        table_name = None
        cname_list = []

        ## read in table column names
        while 1:
            try:
                (s,t) = self.cife.getNextElement()
            except EOFError:
                self.syntax_error('premature end of file')

            ## no more column names, this is data
            if t == "string" or s[0] != '_':
                self.cife.replaceElement((s,t))
                break

            (tname, cname) = s[1:].split(".")

            if table_name != tname:
                if table_name:
                    self.syntax_error('section in loop do not match')
                table_name = tname

            cname_list.append(cname)

        table = mmCIFTable(table_name, cname_list)
        data.addTable(table)

        ## read in table column data
        while 1:
            row = mmCIFRow()
            table.append(row)
            
            for cname in table.getColumnList():
                try:
                    (s,t) = self.cife.getNextElement()
                except EOFError:
                    self.syntax_error('loop values incomplete')

                ## freak out
                if t == "token" and s[0] == '_':
                    self.syntax_error('expected data got section=%s' % (s))

                row[cname] = s

            try:
                (s,t) = self.cife.peekNextElement()
            except EOFError:
                self.done = 1
                break

            ## if the next element is a mmCIF control token, then break
            if t == "token":
                if s[0]  == '_':     break
                if s[:5] == 'data_': break
                if s[:5] == 'loop_': break
                if s[:5] == 'save_': break



class mmCIFDictionaryParser(mmCIFFileParser):
    """Subclassed from mmCIFFileParser and extended to support the additional
    syntax encountered in the dictionary files.  I wrote this quite a while
    ago, and now that I look at it again, I suspect it's not complete."""
    def parseFile(self, fil):
        self.done = 0
        self.cife = mmCIFElementFile(fil)
        try:
            (s,t) = self.cife.getNextElement()
        except EOFError:
            return None

        if s[:5] != 'data_':
            self.syntax_error('unexpected element=%s' % (s))
            
        return self.read_save_list(dict)

    def read_save_list(self, dict):
        save_list = []
        
        while not self.done:
            try:
                (s,t) = self.cife.getNextElement()
            except EOFError:
                self.done = 1
                break

            if s[0] == '_':
                self.read_single(data, s)

            elif s[:5] == 'save_':
                save = self.read_save(mmCIFData(), s)
                save_list.append(save)
                
            elif s[:5] == 'loop_':
                self.read_loop(s)

            elif s[:5] == 'data_':
                self.syntax_error('two data_ subsections in dictionary')

            else:
                self.syntax_error('bad element=%s' % (s))

        return save_list

    def read_save(self, data, s):
        if s[:6] == 'save__':
            name = s[6:]
        else:
            name = s[5:]

        if not name:
            self.syntax_error('expected opening save_ block')

        self.read_data(data)
        try:
            (s,t) = self.cife.getNextElement()
        except EOFError:
            self.done = 1
        else:
            if s != 'save_':
                self.sytax_error('expected closing save_ block')
        
        return data

    def read_data(self, data):
        while not self.done:
            try:
                (s,t) = self.cife.getNextElement()
            except EOFError:
                self.done = 1
                break

            if s[0] == '_':
                self.read_single(data, s)
                
            elif s[:5] == 'loop_':
                self.read_loop(data, s)

            elif s[:5] == 'data_':
                self.syntax_error('two data_ subsections in dictionary')
                break

            elif s[:5] == 'save_':
                self.cife.replaceElement((s,t))
                break
            
            else:
                self.syntax_error('bad element=%s' % (s))



class mmCIFFileWriter:
    """Writes out a mmCIF file using the data in the mmCIFData list."""  

    def writeFile(self, fil, cif_data_list):
        self.fil = fil

        ## constant controlls the spacing between columns
        self.SPACING = 2

        ## iterate through the data sections and write them
        ## out to the file
        for cif_data in cif_data_list:
            self.cif_data = cif_data
            self.write_cif_data()

    def write(self, line):
        self.fil.write(line)

    def writeln(self, line = ""):
        self.fil.write(line + "\n")

    def fix_value(self, val):
        ## make sure the value is a string
        val = str(val)

        ## blank values are not allowd -- replace them with
        ## question marks
        if not len(val): return "?"

        ## quote strings with spaces
        if val.find(" ") != -1: return "'%s'" % (val)

        ## don't do anything to the value if we make it here
        return val

    def fix_big_string(self, val):
        ## large strings -- break them up into newlined chunks < size
        if len(val) > MAX_LINE-1:
            tmp = []
            for x in val.split("\n"):
                while len(x) > MAX_LINE-1:
                    tmp.append(x[:MAX_LINE-1])
                    x = x[MAX_LINE-1:]
                tmp.append(x)
            return string.join(tmp, "\n")

        return val

    def write_cif_data(self):
        self.writeln("data_%s" % self.cif_data.getName())
        self.writeln("")
        
        for cif_table in self.cif_data:
            if   len(cif_table) == 0: continue
            elif len(cif_table) == 1: self.write_one_row_table(cif_table)
            else:                     self.write_multi_row_table(cif_table)
            self.writeln("#")

    def write_one_row_table(self, cif_table):
        row = cif_table[0]

        kmax  = 0
        for col in cif_table.columns:
            key = "_%s.%s" % (cif_table.name, col)
            kmax = max(kmax, len(key))

        ## we need a space after the tag
        kmax += self.SPACING

        for col in cif_table.columns:
            key = "_%s.%s" % (cif_table.name, col)
            self.write(key.ljust(kmax))

            try:
                val = row[col]
            except KeyError:
                val = "?"

            fval = self.fix_value(val)
            
            if   len(fval) > MAX_LINE-1:
                fval = self.fix_big_string(val)
                self.writeln()
                self.writeln(";" + fval)
                self.writeln(";")

            elif len(fval) > MAX_LINE-kmax-1: 
                self.writeln()
                self.writeln(fval)

            else:
                self.writeln(fval)

    def write_multi_row_table(self, cif_table):
        self.writeln("loop_")
        for col in cif_table.columns:
            self.writeln("_%s.%s" % (cif_table.name, col))

        ## initalize a vmax list, the list of the maximum width
        ## of that column in all the rows
        vmax = [0 for x in cif_table.columns]

        ## optimization
        col_tuple = [(cif_table.columns[i], i) \
                     for i in range(len(cif_table.columns))]

        for row in cif_table:
            for (col, i) in col_tuple:
                try:
                    val = row[col]
                except KeyError:
                    val = "?"
                val = self.fix_value(val)
                vmax[i] = max(vmax[i], len(val))
                
        ## now we know the maximum width of each field, so we can start
        ## writing out rows
        for row in cif_table:
            wlen = MAX_LINE-1
            
            for (col, i) in col_tuple:
                try:
                    val = row[col]
                except KeyError:
                    val = "?"

                ## we don't have enough space left on this line
                if vmax[i]+self.SPACING > wlen and wlen < MAX_LINE-1:
                    self.writeln()
                    wlen = MAX_LINE-1

                ## write out the value
                if vmax[i] > MAX_LINE-1:
                    fval = self.fix_big_string(val)
                    self.writeln(";" + fval)
                    self.writeln(";")

                else:
                    if wlen < MAX_LINE-1:
                        self.write("".ljust(self.SPACING))
                        wlen -= self.SPACING

                    fval = self.fix_value(val)
                    self.write(fval.ljust(vmax[i]))
                    wlen -= vmax[i]

            if wlen < MAX_LINE-1:
                self.writeln()


                
##
## <testing>
##

if __name__ == '__main__':
    import sys

    try:
        path = sys.argv[1]
    except IndexError:
        print "usage: mmCIF.py <mmCIF file path>"
        sys.exit(1)

    cif = mmCIFFile()
    cif.loadFile(path)
    cif.saveFile(sys.stdout)

##
## </testing>
##
