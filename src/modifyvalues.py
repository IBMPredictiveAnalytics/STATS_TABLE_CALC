#/***********************************************************************
# * Licensed Materials - Property of IBM 
# *
# * IBM SPSS Products: Statistics Common
# *
# * (C) Copyright IBM Corp. 1989, 2020
# *
# * US Government Users Restricted Rights - Use, duplication or disclosure
# * restricted by GSA ADP Schedule Contract with IBM Corp. 
# ************************************************************************/

# format specific rows or columns in a pivot table of given type


__author__ = "JKP, IBM SPSS"

# This module requires at least SPSS 18.0.0

# history
# 02-jul-2012 original version
# 24-jul-2012 handle invalid input values better
# 16-niv-2014 make math module accessible in formulas
# 30-mar-2015 Force sysmis values to not operate arithmetically



import spss, SpssClient, spssaux
from extension import  _isseq
import re, sys, copy, operator, random, math
import gc

v21001ok = spss.__version__.split(".") >= "21.0.0.1".split(".")  # need the bugfix in insert apis
SYSMIS = -1.7976931348623157e+308  # used to force SYSMIS values not to compute as arithmetic


def modify(subtype, location, formula, targetlabel, mode="replace",
           skiplog=True, process="preceding", dimension='columns',
           level=-1, hide=False, width=None, cellformat="asis", decimals=2, repeatloc=False,
           printlabels=False, floatfail="", custommodule=None, nextsubtype=None, prevsubtype=None,
           align = "asis"):
    """Apply a hide or show action to specified columns or rows of the specified subtype or resize columns

    subtype is the OMS subtype of the tables to process or a sequence of subtypes
    location is a sequence of column or row identifiers or ["ALL"].  Identifiers can be
    positive or negative numbers, counting from 0.  Negative numbers count from
    the end: -1 is the last row or column.
    Identifiers can also be the text of the lowest level in the column heading.
    If the value is or can be converted to an integer, it is assumed to be a column number.
    Numeric values are truncated to integers.
    repeatloc causes the location sequence to be repeated throughout the dimension
    You cannot hide all the items even though this routine will try.
    process specifies "preceding" to process the output of the preceding command or "all"
    to process all tables having any of the specified subtypes.
    level defaults to the innermost level (-1).  Specify a more negative number to move out or up in
    the label array.  -2, for example, would be the next-to-innermost level.
    When counting columns or rows, count at the innermost level regardless of the level setting.
    Hide cannot be combined with other actions.
    if skiplog is True, if the last item in the Viewer is a log, the search starts with the preceding item.
    It needs to be True if this function is run from the extension command and commands are echoing to the log.
    dimension == 'columns' indicates that columns should be operated on.  dimension == 'rows' specifies rows.
    width specifies the width to be applied to the selected rows or columns
    nextsubtype and prevsubtype are OMS subtypes for a secondary table.  They can only be
    used with a custom function and only one or the other can be specified.


    This function processes the latest item in the designated Viewer: all pivot tables for that instance of
    the procedure are processed according to the subtype specification.
"""
    # ensure localization function is defined
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg

    # debugging
    # makes debug apply only to the current thread
    #try:
        #import wingdbstub
        #if wingdbstub.debugger != None:
            #import time
            #wingdbstub.debugger.StopDebug()
            #time.sleep(1)
            #wingdbstub.debugger.StartDebug()
        #import thread
        #wingdbstub.debugger.SetDebugThreads({thread.get_ident(): 1}, default_policy=0)
        ## for V19 use
        ##    ###SpssClient._heartBeat(False)
    #except:
        #pass

    if spssaux.GetSPSSMajorVersion() < 21 and mode != "replace":
        raise ValueError(_("""Only replace mode can be used in Statistics version 20 or earlier"""))
    applied = False
    SpssClient.StartClient()
    try:
        info = NonProcPivotTable("TABLESTRUCTURE", tabletitle=_("Table Structure"))
        c = PtColumns(dimension, level, hide, width, location, targetlabel, mode,
            formula, cellformat, decimals, printlabels, floatfail, custommodule, align, repeatloc)
        subtype = cleansubtypes(subtype)
        if nextsubtype and prevsubtype:
            raise ValueError(_("""Only one of next and previous subtype specifications can be used"""))
        if (nextsubtype or prevsubtype) and not custommodule:
            raise ValueError(_("""A secondary table can only be used with a custommodule"""))
        nextsubtype = cleansubtypes(nextsubtype)
        prevsubtype = cleansubtypes(prevsubtype)

        items = SpssClient.GetDesignatedOutputDoc().GetOutputItems()
        itemcount = items.Size()
        if skiplog and items.GetItemAt(itemcount-1).GetType() == SpssClient.OutputItemType.LOG:
            itemcount -= 1
        for itemnumber in range(itemcount-1, -1, -1):
            item = items.GetItemAt(itemnumber)
            if process == "preceding" and item.GetTreeLevel() <= 1:
                break
            if item.GetType() == SpssClient.OutputItemType.PIVOT and\
               (subtype[0] == "*" or "".join(item.GetSubType().lower().split()) in subtype):
                c.thetable = item.GetSpecificType()
                applied = True
                c.formula.secondary = getsecondary(items, nextsubtype, prevsubtype, itemnumber, itemcount)
                c.applyaction(c.thetable, info) 

    finally:
        info.generate()
        SpssClient.StopClient()
    if not applied:
        raise ValueError(_("""No tables of the specified type were found to update"""))

def cleansubtypes(subtype):
    """Regularize subtype specification and return as list"""
    
    if subtype is None:
        return [None]
    if not _isseq(subtype):
        subtype=[subtype]
    # remove white space
    subtype = ["".join(st.lower().split()) for st in subtype]
    # remove matching outer quotes of any type
    subtype = [re.sub(r"""^('|")(.*)\1$""", r"""\2""", st) for st in subtype]
    if "*" in subtype:
        subtype = ["*"]
    return subtype

def getsecondary(items, nextsubtype, prevsubtype, itemnumber, itemcount):
    """Return secondary table if requested or None
    
    items is the Viewer item list
    nextsubtype or prevsubtype are lists that indicate the OMS subtype and direction.
        Assumed only one or the other is specified.
    itemnumber is the current table item number
    itemcount is the number of Viewer items"""
    
    if not (nextsubtype[0] or prevsubtype[0]):
        return None
    direction = nextsubtype[0] and 1 or -1  # look forward or backward
    itemtype = nextsubtype[0] or prevsubtype[0]
    
    # look for table of specified type forward or back relative to current item
    for i in range(itemnumber + direction, direction == 1 and itemcount+1 or 0, direction):
        item = items.GetItemAt(i)
        if item.GetType() == SpssClient.OutputItemType.PIVOT and\
           ("".join(item.GetSubType().lower().split()) == itemtype):
            return item.GetSpecificType()
    raise ValueError(_("""Secondary table not found: %s""") % itemtype)


class PtColumns(object):
    """Modify display characteristics of a pivot table"""

    def __init__(self, dimension, level, hide,
            width, location, targetlabel, mode, formula, cellformat, decimals,
            printlabels, floatfail, custommodule, align, repeatloc):
        """location is a sequence of targe locations to modify or insert.
        It can include positive or negative numbers (or things that can be converted to these) and
        strings that will be matched to the lowest level of the column labels ignoring case.
        If dimension == 'rows' then rows are processed instead of columns.
        'rows' cannot be combined with 'width'
        level specifies which level to check.  -1 is the innermost.  This only affects the behavior
        when using specific labels.
        width is a sequence that specifies the width in points
        to be applied to the specified columns.
        secondary will be created as None or secondary table object
        '"""

        attributesFromDict(locals())  # copy parameters

        if not _isseq(location):
            raise ValueError(_("Target specification must be a sequence of one or more values"))
        if width:
            if dimension == 'rows':
                raise ValueError(_("The rows dimension cannot be combined with resizing"))

        self.formula = Formula(formula, targetlabel, cellformat, decimals, hide, width, floatfail, 
            custommodule, align)

    def applyaction(self, pt, info):
        """Apply specified computation to a pivot table.

        pt is the pivot table to process, on which GetSpecificType() is assumed to have been called."""

        # stop if the specified table dimension has true nesting and not using replace mode

        pm = pt.PivotManager()
        if self.mode != "replace":
            if self.dimension == "columns":
                ndim = pm.GetNumColumnDimensions()
            else:
                ndim = pm.GetNumRowDimensions()
            if ndim > 1:
                raise ValueError(_("""Cannot apply command to this table, because it has nested dimensions.
Number of dimensions: %s""") % ndim)
        nlayer = pm.GetNumLayerDimensions()
        if nlayer > 0:
            ldim = pm.GetLayerDimension(0)
            ncat = ldim.GetNumCategories()
            if nlayer > 1 or ncat > 1:
                raise ValueError(_("""Tables with layers with multiple categories or multiple dimensions are not supported"""))

        
        self.datacells = pt.DataCellArray()
        self.rowlabelarray = pt.RowLabelArray()
        self.columnlabelarray = pt.ColumnLabelArray()

        self.numdatarows = self.datacells.GetNumRows()
        self.numdatacols = self.datacells.GetNumColumns()

        if self.dimension == 'columns':
            self.labels = self.columnlabelarray
            rowsorcols = self.labels.GetNumColumns()
            last = self.labels.GetNumRows()
            self.printtablelabels(last, rowsorcols, "Columns", info)
        else:
            self.labels = self.rowlabelarray
            rowsorcols = self.labels.GetNumRows()
            last = self.labels.GetNumColumns()
            self.printtablelabels(rowsorcols, last, "Rows", info)

        try:
            pt.SetUpdateScreen(False)
            if self.level < 0:
                self.level += last   # convert to absolute form
            self.formula.bind(pt, self.location, self.level, self.mode, self.dimension, self.repeatloc)
            self.formula.evaluate()
            # update the table, inserting or replacing results
            self.formula.updatetable(pt)
        finally:
            pt.SetUpdateScreen(True)
    
    def printtablelabels(self, rows, cols, which, info):
        """Print row or column labels of table

	rows and cols are the dimensions.
	which is "rows" or "columns"."""
        if self.printlabels:
            info.addrow(_("Table Labels: %s.  Dimensions: %s, %s") % (which, rows, cols))
            for i in range(rows):
                for j in range(cols):
                    info.addrow("%d %d: %s" % (i, j, self.labels.GetValueAt(i, j)))


def attributesFromDict(d):
    """build self attributes from a dictionary d."""

    # based on Python Cookbook, 2nd edition 6.18

    self = d.pop('self')
    for name, value in d.items():
        setattr(self, name, value)

class Formula(object):
    """formula manager"""
    def __init__(self, formula, targetlabel, cellformat, decimals, hide, width, floatfail, custommodule, align):
        """Prepare formula for evaluation against table
        
        formula rules:
        Python expression using standard operators plus any function in math (without math prefix)
        Cells are references in the same dimension.
        Variables in the formula can be absolute references in the form xn where n is an integer position
        or relative references of the form
        x[item] where item is a relative row or column number or the label text at level.
        Negative numbers refer to before values and positive to after.
        If item is a label, it must be quoted and must be preceded by - or + to indicate preceding or following.
        E.g. x[-'difference'] refers to the first row or column to the left of the insertion 
        or replacement point that is labelled "difference"
        References refer to rows or columns before any insertions.  
        In replace mode, x[-0] refers to the cell being replaced
        In insertbefore or inserafter mode, x[-0] refers to the cell just to the left of the insertion point
        References that do not match or are outside the table raise an exception
        
        formula is the formula
'"""
        
        attributesFromDict(locals())

        self.absrefs = re.findall(r"""x\d+""", self.formula)  # x1, x2, x999
        self.relnumrefs = re.findall(r"""x\[[+-]?\d+\]""", self.formula)   # x[-3], x[+3], x[3], ...
        self.rellabelrefs = re.findall(r"""x\[[+-]?['"].+?['"]\]""", self.formula)   # x[-"abc"], x["abc"], x[+"abc"]
        if custommodule:
            try:
                self.thecustommodule = __import__(custommodule)  # returns the module object
            except:
                raise ImportError(_("""The specified custom module could not be loaded: %s""") % custommodule)
        self.custom = {}   # for use by a custom function
        self.custom["firstload"] = True

    def bind(self, pt, location, level, mode, dimension, repeatloc):
        """bind references to the current table and prepare for evaluation
        
        pt is the pivot table
        labels is the row or column label object as target
        level is the label level (rows if dimension = columns and columns if rows in positive form)
        mode is 'replace', 'insertbefore', or 'insertafter'
        dimension is 'column' or 'row
        repeatloc indicates whether to extend location list to match dimension'"""
        
        attributesFromDict(locals())

        self.results = []   #each list item is the set of results for one occurrence
        
        self.datacells = pt.DataCellArray()
        self.secondarydatacells = self.secondary and self.secondary.DataCellArray() or None
        self.labelvalues = []
        if dimension == "columns":
            self.labels = pt.ColumnLabelArray()
            self.labelsize = self.labels.GetNumColumns()
            for v in range(self.labelsize):
                self.labelvalues.append(self.labels.GetValueAt(self.level, v))
        else:
            self.labels = pt.RowLabelArray()
            self.labelsize = self.labels.GetNumRows()
            for v in range(self.labelsize):
                self.labelvalues.append(self.labels.GetValueAt(v, self.level))
                
                
        # find insert locations for relative calculations - if it looks like an int, it's an absolute reference
        self.insertpoint = []
        labelscpy = copy.copy(self.labelvalues)  # in order to find each only once
        
        loclen = len(location)  # length before any implied extension
        # If repeating locations, extend location list to the number of labels
        if repeatloc:
            self.location = ((self.labelsize + loclen-1) / loclen) * location
            self.location = self.location[:self.labelsize]
            
        for i, item in enumerate(self.location):
            try:
                loc = int(item)
                if self.repeatloc:
                    raise ValueError(_("""Repeating locations can only be used with label text"""))
                if loc < 0:
                    loc += self.labelsize
                if not (0 <= loc < self.labelsize):
                    raise ValueError(_("""A specified row or column label number is outside the table: %s""") % loc)              
            except:  # Using labels
                try:
                    loc = labelscpy.index(item)
                    labelscpy[loc] = None  # strike out value once it has been found
                # could be no such label or could be overexended repeat
                # at least the first instace of every item in the location spec must be found
                except:
                    if i < loclen or not repeatloc:
                        raise ValueError(_("""Specified target location does not match any existing label: %s""") % item)
                    else:
                        self.location = self.location[:i]
                        break
            self.insertpoint.append(loc)

        # create a formula with resolved locations for each target location
        # each list item is a duple consisting of the modified formula and the list of input locations
        self.formulalist = []
        for loc in self.insertpoint:
            self.formulalist.append(self.binder(loc))
        self.custom["firsttable"] = True
        
    def binder(self, loc):
        """return evaluation structure duple: modified formula and list of input locations"""
        
        inputs = []
        # inputs indicated by label
        for item in self.rellabelrefs:
            if re.search(r"\[-", item) is not None:
                direction = -1
                dirtext = _("left or up")
            else:
                direction = 1
                dirtext = _("right or down")
            labeltext = re.search(r"""\[[+-]?['"](.*?)['"]\]""", item).group(1)
            if direction > 0:
                args = [loc, self.labelsize]
            else:
                args = [loc, -1, -1]
            for i in range(*args):
                if self.labelvalues[i] == labeltext:
                    inputs.append(i)
                    break
            else:
                raise ValueError(_("""A specified input label was not found: %s, search direction from target: %s""") % (labeltext, dirtext))

        # relative numeric references
        for item in self.relnumrefs:
            number = int(re.search(r"""\[(.*)\]""", item).group(1))
            absloc = loc + number
            if not 0 <= absloc < self.labelsize:
                raise ValueError(_("""A specified relative row or column number is outside the table: %s""") % number)
            inputs.append(absloc)
        # absolute references
        for item in self.absrefs:
            item = int(item[1:])
            if not 0 <= item <self.labelsize:
                raise ValueError(_("""An absolute cell reference is outside the table: %s""" % item))
            inputs.append(item)
        # modify the formula to use positional references.  absolute refs are already okay
        executionformula = self.formula
        i = 0
        for item in self.rellabelrefs:
            executionformula = executionformula.replace(item, "x" + str(inputs[i]))  # todo: repeats?
            i += 1
        for item in self.relnumrefs:
            executionformula = executionformula.replace(item, "x" + str(inputs[i]))
            i += 1
        return (executionformula, inputs)    
            
    def evaluate(self):
        """accumulate result rows or columns for each target cell"""
        
        for i, target in enumerate(self.location):
            self.results.append(self.evals(i, self.formulalist[i][0], self.formulalist[i][1]))
                
    def evals(self, resultnumber, formula, inputs):
        """Evaluate formula across the table
        
        resultnumber is the enumeration count - counts target instances
        formula is the prepared formula
        inputs is the list of row or column indexes for the inputs
        For any cell where the evaulation raises an exception, the displayed value 
        comes from the missing setting"""
        
        results = []
        if self.dimension == "columns":
            ncells = self.datacells.GetNumRows()
            cols = True
            ncells2 = self.secondarydatacells and self.secondarydatacells.GetNumRows() or None
        else:
            ncells = self.datacells.GetNumColumns()
            cols = False
            ncells2 = self.secondarydatacells and self.secondarydatacells.GetNumColumns() or None
        inputvalues = {"pt": self.pt, "datacells": self.datacells, "labels": self.labels, "ncells": ncells,
            "arg" : self.custom, "currentloc": self.location[resultnumber], "math":math}
        if self.custommodule:
            # redundantly, parameters can be passed via syntax specification or through
            # a custom dictionary that is automatically created
            inputvalues[self.custommodule] = self.thecustommodule
            self.custom.update({"pt": self.pt, "datacells": self.datacells, "labels": self.labels, 
                "ncells": ncells,"secondary": self.secondary, "ncells2": ncells2, "resultnumber": resultnumber,
                "currentloc": self.location[resultnumber],
                'sdatacells':self.secondary and self.secondary.DataCellArray() or None})
        for roworcol in range(ncells):
            for input in inputs:   # build dictionary of input values
                if cols:
                    args = [roworcol, input]
                else:
                    args = [input, roworcol]
                try:
                    value = float(self.datacells.GetUnformattedValueAt(*args))
                    if value == SYSMIS:
                        value = None
                except:
                    value = None
                inputvalues["x"+str(input)] = value
            try:
                inputvalues["roworcol"] = roworcol
                if('linux' in sys.platform):
                    gc.collect()    #to fix ECM00195231, call the gc.collect() before the dictionary update
                self.custom.update({"roworcol": roworcol, "inputvalues": inputvalues})
                result = eval(formula, inputvalues)
            except (NameError, SyntaxError):
                raise
            except:   # ValueErrors just produce failure value
                result = self.floatfail
            results.append(result)
            
        return results
    
    def updatetable(self, pt):
        """insert or replace table rows or columns with calculated results
        
        pt is the table - provided only so that a screen update can be forced"""
        
        # locations are assumed sorted in descending numerical order
        
        if self.dimension == "columns":
            n = self.datacells.GetNumRows()
            lastlabel = self.labels.GetNumRows()-1
        else:
            n = self.datacells.GetNumColumns()
            lastlabel = self.labels.GetNumColumns() -1
            
        # sort insert points descending and corresponding results for ease of insertion
        # then unzip the results
        insertsandresults = sorted(zip(self.insertpoint, self.results), reverse=True)
        self.insertpoint, self.results = list(zip(*insertsandresults))
        
        templabel = str(random.random())  # need to find out where column was actually put
        for i, loc in enumerate(self.insertpoint):
            if self.dimension == "columns":
                #args = [self.level, loc, self.targetlabel]
                args = [self.level, loc, templabel]
            else:
                #args = [loc, self.level, self.targetlabel]
                args = [loc, self.level, templabel]
            if self.mode == "after":
                self.labels.InsertNewAfter(*args)
            elif self.mode == "before":
                self.labels.InsertNewBefore(*args)
            else:   # replacing values
                self.labels.SetValueAt(*args)
                lastlabel = self.level
            if not v21001ok:
                pt.SetUpdateScreen(True)    # force updated table to be seen
                pt.SetUpdateScreen(False)
            targetloc = self.alignroworcol(lastlabel, templabel, self.targetlabel)
            if self.width:    # can only apply if columns
                self.datacells.ReSizeColumn(targetloc, self.width)

            # insert a row or column of values
            # due to a bug in 21.0.0.0, the decimals value cannot be honored
            # for the first cell of an inserted row or column, so force round as a string
            # just for that cell.  Unavoidable loss of precision, but better than
            # always having a bad display.
            if self.mode != "replace":
                try:
                    self.results[i][0] = str(round(self.results[i][0], self.decimals))
                except:
                    pass
            for cell in range(n):
                if self.dimension == "columns":
                    args1 = [cell, targetloc, str(self.results[i][cell])]
                    args2 = [cell, targetloc, self.cellformat, self.decimals]
                    args3 = [cell, targetloc, SpssClient.SpssHAlignTypes.SpssHAlRight]
                else:
                    args1 = [targetloc, cell, str(self.results[i][cell])]
                    args2 = [targetloc, cell, self.cellformat, self.decimals]
                    args3 = [targetloc, cell, SpssClient.SpssHAlignTypes.SpssHAlRight]
                self.datacells.SetValueAt(*args1)
                self.datacells.SetHAlignAt(*args3)  # should not be necessary
                if not self.cellformat.lower() == "asis":
                    try:
                        self.datacells.SetNumericFormatAtWithDecimal(*args2)           
                    except:
                        raise ValueError(_("""The format or decimals specified for modified cells is not valid: %s, %s""" % (self.cellformat, self.decimals)))
        if self.hide:
            self.hidem(self.dimension, self.labels, self.formulalist, self.insertpoint, self.mode)
    
    horizalign = {"lefttop":SpssClient.SpssHAlignTypes.SpssHAlLeft, 
        "center":SpssClient.SpssHAlignTypes.SpssHAlCenter,
        "rightbottom": SpssClient.SpssHAlignTypes.SpssHAlRight}
    vertalign = {"lefttop": SpssClient.SpssVAlignTypes.SpssVAlTop,
        "center": SpssClient.SpssVAlignTypes.SpssVAlCenter,
        "rightbottom": SpssClient.SpssVAlignTypes.SpssVAlBottom}
    
    def alignroworcol(self, lastlabel, templabel, targetlabel):
        """Align label vertically or horizontally
        
        loc is the row or column in the label array"""
        
        if self.dimension == "columns":
            extent = self.labels.GetNumColumns()
            for i in range(extent):
                if self.labels.GetValueAt(lastlabel, i) == templabel:
                    self.labels.SetValueAt(lastlabel, i, targetlabel)
                    if self.align != "asis":
                        self.labels.SetVAlignAt(lastlabel, i, Formula.vertalign[self.align])
                    break
        else:
            extent = self.labels.GetNumRows()
            for i in range(extent):
                if self.labels.GetValueAt(i, lastlabel) == templabel:
                    self.labels.SetValueAt(i, lastlabel, targetlabel)
                    if self.align != "asis":
                        self.labels.SetHAlignAt(i, lastlabel, Formula.horizalign[self.align])
                    break
        return i
        #if self.align == "asis":
            #return
        #if self.dimension == "columns":
            #self.labels.SetVAlignAt(lastlabel, loc, Formula.vertalign[self.align])
        #else:
            #self.labels.SetHAlignAt(loc, lastlabel, Formula.horizalign[self.align])


    def hidem(self, dimension, labels, parts, targetlocations, mode):
        """hide the rows or columns in parts
        
        labels is the label object        
        parts is the formula structure including the formula and the inputs
        targetlocations is the list of columns or rows for inserts
        mode is the type of insertion"""
        
        # the target columns or rows have already been inserted, so
        # it is necessary to update the input locations to account for this
        # if mode is not replace.
        
        items =[item[1] for item in parts]   # split out the input row or column numbers
        therowsorcols = []
        # extract individual numbers and merge
        for item in items:
            therowsorcols.extend(item) 
        therowsorcols = set(therowsorcols)  # eliminate duplicates
        if mode != "replace":
            adjset = set()
            if mode == "before":
                cop = operator.le
            else:
                cop = operator.lt
            for item in therowsorcols:   # count insertions ahead of input location
                adjcount = len([targetitem for targetitem in targetlocations if cop(targetitem,item)])
                adjset.add(item + adjcount)
            therowsorcols = adjset
            
        if dimension == "columns":
            nrow = labels.GetNumRows()
            for item in therowsorcols:
                labels.HideLabelsWithDataAt(nrow-1, item)
        else:
            ncol = labels.GetNumColumns()
            for item in therowsorcols:
                labels.HideLabelsWithDataAt(item, ncol-1)
            

class NonProcPivotTable(object):
        """Accumulate an object that can be turned into a basic pivot table once a procedure state can be established"""
        
        def __init__(self, omssubtype, outlinetitle="", tabletitle="", caption="", rowdim="", coldim="", columnlabels=[],
                     procname="Messages"):
                """omssubtype is the OMS table subtype.
                caption is the table caption.
                tabletitle is the table title.
                columnlabels is a sequence of column labels.
                If columnlabels is empty, this is treated as a one-column table, and the rowlabels are used as the values with
                the label column hidden
                
                procname is the procedure name.  It must not be translated."""
                
                attributesFromDict(locals())
                self.rowlabels = []
                self.columnvalues = []
                self.rowcount = 0
        
        def addrow(self, rowlabel=None, cvalues=None):
            """Append a row labelled rowlabel to the table and set value(s) from cvalues.
            
            rowlabel is a label for the stub.
            cvalues is a sequence of values with the same number of values are there are columns in the table."""
                
            if cvalues is None:
                cvalues = []
            self.rowcount += 1
            if rowlabel is None:
                    self.rowlabels.append(str(self.rowcount))
            else:
                    self.rowlabels.append(rowlabel)
            if not _isseq(cvalues):
                    cvalues = [cvalues]
            self.columnvalues.extend(cvalues)
            
        def generate(self):
                """Produce the table assuming that a procedure state is now in effect if it has any rows."""
                
                privateproc = False
                if self.rowcount > 0:
                    import spss
                    try:
                            table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
                    except:
                            StartProcedure(_("Messages"), self.procname)
                            privateproc = True
                            table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
                    if self.caption:
                            table.Caption(self.caption)
                    # Note: Unicode strings do not work as cell values in 18.0.1 and probably back to 16
                    if self.columnlabels != []:
                            table.SimplePivotTable(self.rowdim, self.rowlabels, self.coldim, self.columnlabels, self.columnvalues)
                    else:
                            table.Append(spss.Dimension.Place.row,"rowdim",hideName=True,hideLabels=True)
                            table.Append(spss.Dimension.Place.column,"coldim",hideName=True,hideLabels=True)
                            colcat = spss.CellText.String("Message")
                            for r in self.rowlabels:
                                    cellr = spss.CellText.String(r)
                                    table[(cellr, colcat)] = cellr
                    if privateproc:
                            spss.EndProcedure()
def _isseq(obj):
        """Return True if obj is a sequence, i.e., is iterable.
        
        Will be False if obj is a string or basic data type"""
        
        if isinstance(obj, str):
                return False
        else:
                try:
                        iter(obj)
                except:
                        return False
                return True

def StartProcedure(procname, omsid):
    """Start a procedure
    
    procname is the name that will appear in the Viewer outline.  It may be translated
    omsid is the OMS procedure identifier and should not be translated.
    
    Statistics versions prior to 19 support only a single term used for both purposes.
    For those versions, the omsid will be use for the procedure name.
    
    While the spss.StartProcedure function accepts the one argument, this function
    requires both."""
    
    import spss
    try:
        spss.StartProcedure(procname, omsid)
    except TypeError:  #older version
        spss.StartProcedure(omsid)
