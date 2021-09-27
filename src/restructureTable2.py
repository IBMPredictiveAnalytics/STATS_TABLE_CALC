# restructure CTABLES table rows and merge sig level statistics from Chi-squared and subsequent ONEWAY procedure

# f is custom function for restructuring rows.
# g is custom function for sig level merging.

# Jon Peck
# History
# 10-jun-2017 original version


import SpssClient
import re

def f(arg):
    """for means, replace with mean +- std dev (adjacent column)
    for counts, replace with count (percent%) (adjacent column)
    
    arg is the dictionary provided by STATS TABLE CALC and referenced in formula
    formula="restructureTable2.f(arg)"
    """
    
    datacells = arg['datacells']
    roworcol = arg['roworcol']
    resultnumber = arg['resultnumber']
    # prepare to track result columns
    # table columns assumed to be for each column category
    # current column will be "Mean" when f is called
    if arg['firsttable']:
        arg['firsttable'] = False
        arg['plusminus'] = chr(0xb1)
        ll = arg['labels']
        # find Count location relative to Mean location (up to +/- 3)
        t = arg['insertpoints'][resultnumber]    
        llrows = ll.GetNumRows()
        llcols = ll.GetNumColumns()
        for offset in range(-3, 3):
            if 0 <= t + offset <= llcols - 1:
                if ll.GetValueAt(llrows-1, t + offset) == "Count":
                    arg["offset"] = offset
                    break    # assuming column will always be found
            
    t = arg['insertpoints'][resultnumber]   # current target table location
    v = datacells.GetValueAt(roworcol, t).rstrip()
    if v != "":
        return "%s %s %s" % (v, arg['plusminus'], datacells.GetValueAt(roworcol, t+1))  # (current value, adjacent value)
    else:
        v = datacells.GetValueAt(roworcol, t + arg['offset'])
        vpct = datacells.GetValueAt(roworcol, t + arg['offset'] + 1)
        if vpct != "":
            return "%s (%s)" % (v, vpct)   # (value two cols to the right, value three columns to the right)
        else:
            return "%s" % v
    
def g(arg):
    """return sig level from secondary tables or None
    
    arg is the dictionary from STATS TABLE CALC and referenced as
    formula="restructureTable2.g(arg)"
    """
    
    if arg['firsttable']:
        # build dictionary of sig values - first from CTABLES chi-squared table
        # then from ONEWAY anova table
        
        arg['firsttable'] = False
        sdatacellslist = arg['sdatacells']
        sptlist = arg['secondary']
        llseclist = [item.RowLabelArray() for item in sptlist]
        ###arg['llseclist'] = [item.RowLabelArray() for item in arg['pt']]
        arg['llseclist'] = llseclist
        arg['ll'] = arg['pt'].RowLabelArray()   # main table labels
        srowslist = [item.GetNumRows() for item in llseclist]
        arg['sigdict'] = {}
        # first do chi-squared table
        llsec = llseclist[0]
        for r in range(srowslist[0]):
            if llsec.GetValueAt(r, 2) == "Sig.":
                var = llsec.GetValueAt(r, 1)
                arg['sigdict'][var] = sdatacellslist[0].GetValueAt(r, 0)
                
        # anova table sig values
        llsec = llseclist[1]
        sigcol = sdatacellslist[1].GetNumColumns() - 1
        for r in range(srowslist[1]):
            sigval = sdatacellslist[1].GetValueAt(r, sigcol)
            if sigval != "":
                var = llsec.GetValueAt(r, 1)
                arg['sigdict'][var] = sigval
                
                
    # return sig value for current row if there is one in the secondary table
    curlbl = arg['ll'].GetValueAt(arg["roworcol"], 1)    #keyed by second level of row label as first is hidden "ROW"
    if curlbl == "":
        curlbl = arg['ll'].GetValueAt(arg["roworcol"], 2)
    if curlbl in arg['sigdict']:
        result = arg['sigdict'][curlbl]
        result = re.sub(r",*b,*|c", "", result)   # remove footnote superscripts, if any
        del arg['sigdict'][curlbl]    # only return sig value once
    else:
        result = ""
    return result
    

    