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

# SPSSINC MODIFY TABLES extension command

"""This module implements the STATS TABLE CALC extension command.
It delegates the implementation to the modifyvalues.py module."""

__author__ = "SPSS, JKP"
__version__ = "1.1.3"

# history
# sept-01-12 original version
# jan-02-13 enhancements for secondary tables, handle more table types, REPEATLOC, and ALIGN
# feb-20-13 add currentloc access for custom functions

from extension import Template, Syntax, processcmd

import modifyvalues


helptext="""STATS TABLE CALC SUBTYPE=subtypes [NEXTSUBTYPE=subtype] [PREVSUBTYPE=subtype]
    [PROCESS={PRECEDING* | ALL}
    [PRINTLABELS={NO* | YES}]
/TARGET [DIMENSION={COLUMNS* | ROWS}] LEVEL=number
    FORMULA = "formula for new values"
    LOCATION=numbers or labels MODE={REPLACE* | BEFORE | AFTER} REPEATLOC={NO*|YES}
    LABEL= "label text"
    CUSTOMMODULE= "module name"
    [HIDEINPUTS = {NO* | YES}
[/FORMAT [WIDTH=number in points] [CELLFORMAT = "format expression"]
[DECIMALS=number] [INVALID = "symbol for invalid values"] ALIGN={ASIS*|LEFTTOP CENTER |RIGHTBOTTOM}]
[/HELP].

Example:
STATS TABLE CALC SUBTYPE="custom table"
/TARGET DIMENSION=columns LEVEL=-2 LOCATION=0 MODE=before LABEL="clerical+manager"
FORMULA="x[-'Clerical'] + x[-'Manager']".

This command does calculations on pivot tables putting the results in either new rows or columns
or replacing existing values.  While it works with most pivot tables, it cannot be used when
there is true nesting of dimensions in the specified dimension except when using replace.
Note that Custom Tables output may appear to be nested, those tables do not have true
nesting.  Tables with multiple layer dimensions or multiple categories in one layer dimension
are not supported.

SUBTYPE is the OMS table subtype   It specifies which types of tables to process.
You can find the subtype by right clicking in the outline on an instance 
or from Utilties/OMS identifiers.
The subtype name should be in quotes.  Any extra matching outer quotes are removed.
Case and white space do not matter.  Multiple subtypes can be specified.
SUBTYPE="*" processes tables regardless of subtype.

By default, the immediately preceding procedure output is processed.  Specify
PROCESS=ALL to process all existing tables matching the specified subtypes.

By default, when selecting by the row or column header text, the lowest or
innermost text is tested.  LEVEL can be specified to use outer layers
of the labels.  LEVEL=-1, the default, is the innermost layer.  More negative
numbers move out.  Positive numbers  count in from the outside.  
LEVEL=1 is usually the first visible cell (level 0 is the dimension label).

In some cases, there may be invisible levels inbetween
what you see, so some experimentation may be required to find the level
you need.  The level specification only affects text matching.  Column and row
numbers always count at the innermost level.

Use PRINTLABELS=TRUE to display the full label structure of selected tables
in the specified dimension in order to assist in specifying the level.

DIMENSION=COLUMNS, the default, indicates operating on columns.
DIMENSION=ROWS causes rows to be operated on.

LOCATION specifies where the results should go.  It can be one or more
row or column numbers, or it can refer to the label value at the specified level.
E.g., LOCATION=3 refers to the fourth column or row.  LOCATION="Total"
refers to the column or row labelled "Total".  LOCATION="Total" "Total"
refers to the first two columns or rows labelled Total.
All label references are case sensitive.

REPEATLOC specifies whether the specified location or sequence of
locations should be repeated for all instances of the LOCATION specification
For example, if LOCATION = 'a' 'b' and REPEATLOC=YES, the location
specification would be treate as 'a' 'b' 'a' 'b' ... until the end of the dimension.
It does not make sense to specify YES if the LOCATION specification is numeric.

MODE specifies how the location is interpreted.  
If MODE=REPLACE, the values at column or row LOCATION are replaced.  
Only this mode can be used in Statistics version 20 or earlier.
If MODE=BEFORE, a new column or row is inserted at that location,
and every later column or row is moved over by one.  Use this mode to
create a new first column or row with LOCATION=0
If MODE=AFTER, a new column or row is inserted after that location.
Use this mode to create a new last column or row.

LABEL specifies the label text for the target row or column.

FORMULA specifies the computation to be carried out.  For COLUMNS, it
is applied to each row, and for ROWS, it is applied to each column.  The entire
formula must be enclosed in quotation marks.

The formula can use the standard arithmetic operators (use ** for power) and 
standard mathematical functions such as min, max, mod, trunc, abs, exp, 
log (base e, use log(x,10 for base 10).
It must be valid Python syntax except as explained below.  See the Python 
documentation, including the math module, for a complete list.

Row or coumn values in the table can be referred to in three ways.  All of these
are evaulated BEFORE any items are added to the tables.
References of the form xn, where n is an integer e.g., x2, refer to the absolute 
column or row.  Numbering starts from zero, so x0 is the first column or row.

References of the form x[n] or x[-n] refer to values to the left or right (above or below)
of the target location.  E.g., x[-1] refers to the location immediately left of the target location
if using columns or immediately above it for rows.  x[1] is the location immediately to the right.
x[0] is the target location itself (before the target is inserted).

Example:  suppose there are columns with labels a, b, and c, and the target
location is c.  Then x[0] refers to the value at c, x[-1] refers to b, and x[-2]
refers to a, regardless of the mode setting.


References of the form x['string'] or x[-'string'] refer to values to the left or right
(above or below) of the target location where string is the value of the label at 
the specified level.  E.g., x[-"Clerical"] refers to the nearest column to the left 
of the target location that is labelled "Clerical".  

Note that the strings must be quoted.  The bracket notation does NOT refer to
Python dictionaries but is used here to refer to locations.

If a reference looks like a number, it is interpreted accordingly.  So you can't refer
to a label that is actually numeric.  Such labels are typically data values, so you can
get around this by assigning a value label.  Here is an example using the
employee data.sav file shipped with Statistics.  The table has the education values
in the rows, and the table calc command inserts a subtotal of grades 8 and 12
after the newly labelled value of 12.  Of course this presumes that there are exactly
two numbers to sum.  Note also that the target location, "HS", is repeated so that
the calculation is done twice.

value labels educ 12 "HS".
CTABLES
  /TABLE minority >educ [COUNT F40.0] BY jobcat
  /CATEGORIES VARIABLES=minority educ jobcat ORDER=A TOTAL=YES.

STATS TABLE CALC SUBTYPE="custom table" PROCESS=ALL
/TARGET DIMENSION=rows LEVEL=-1 LOCATION="HS" "HS" "HS" MODE=after LABEL="HS Subtotal"
FORMULA="x[0] + x[-1]" .

CUSTOMMODULE can specify a Python module whose functions can be
used in the formula.  This can be useful when you need to refer to values
outside the row or column of the current cell.  See the example below.

HIDEINPUTS=YES causes the input rows or columns in the formula to be hidden.

Specify WIDTH=number to set the width of the target
columns to the specified values in points (one point = 1/72 inch).
WIDTH cannot be used with DIMENSION=ROWS.

FORMAT specifies the format for the column or row.
CELLFORMAT="asis", which is the default leaves the format unchanged in 
REPLACE mode and uses the default format for new columns or rows.
Other formats are as specified in the Cell Formats dialog box list in the pivot table
editor.  Examples include
"#,###.##" and "##.#%"
The number of decimal places can be specified with the DECIMALS keyword.

ALIGN can be used to set the label alignment to top, center, or bottom for
columns and left, center, or right for rows.  However, this keyword has no
effect in Statistics 21.0.0.0 or earlier.

INVALID specifies the symbol to be used when a value cannot be computed.
By default, it is a blank.

/HELP displays this text and does nothing else.

Using a Custom Module in a formula

A custom module can have access to the entire pivot table and/or a secondary table.  Here is an
example where the total in a crosstabs table is used in calculation for each row.
CROSSTABS  /TABLES=jobcat BY gender  /CELLS=COUNT.
This command uses a custom function in order to access the overall
total in the table.
STATS TABLE CALC SUBTYPE='Crosstabulation'
/TARGET DIMENSION=COLUMNS LEVEL=-1 LOCATION="Total" MODE=REPLACE LABEL="Ratio"
CUSTOMMODULE="customexample" 
FORMULA = "customexample.custom(datacells, ncells, datacells.GetValueAt(roworcol, 0))". 

Here is the function in the customexample module:

def custom(datacells, ncells, value):
  '''Calculate percent of total'''
  
  x = float(datacells.GetUnformattedValueAt(ncells-1,2))  # total
  return  float(value) / x
  
Notes:
The following variables are available for use in the formula as function parameters.

pt - the pivot table object 
datacells - the datacells object of the pivot table
labels - the row or column labels object corresponding to the DIMENSION setting
ncells - the number of rows or columns in the datacells object.  I.e., if DIMENSION
is columns, it is the number or rows.
roworcol - the current row or column in the table.
currentloc - the current target column or row in the table
arg - a dictionary that the custom function can use to store items across
calls.  It contains at least two entries initially.  These are solely for use by the user
function and have no effect on operation of this command.
"firstload" - True.
"firsttable" - set to True each time a new table is evaluated.
It is up to the user code to set these to False appropriately.
See below for additional contents.

The GetUnformattedValueAt method returns a Unicode string.  It must
be converted to a float for computations.

Using a Secondary Table

A nearby table can be used in parallel with the primary table in
computing new values.
Use PREVSUBTYPE or NEXTSUBTYPE to select the nearest previous or
following table of the specified OMS subtype.  The values in that table
can be combined with or replace values in the first table by using a custom function.  
Here is an example that copies significance results from CTABLES into new columns
in the primary table.

CTABLES  /TABLE gender BY jobcat  /COMPARETEST TYPE=PROP.

STATS TABLE CALC SUBTYPE='customtable' NEXTSUBTYPE  ='Comparisons of Proportions'
/TARGET DIMENSION=COLUMNS LEVEL =-1 LOCATION="Count" "Count" "Count" MODE=AFTER LABEL="Sig."
CUSTOMMODULE="customexample"
FORMULA = "customexample.usesecondary(arg)".

Here is the custom function in customexample.py
def usesecondary(arg):
  return arg['sdatacells'].GetValueAt(arg['roworcol'], arg['resultnumber'])
  
arg is a dictionary containing the following fields.  Note that by passing
arg, the other parameters such as seen above are not necessary, because
those values are included in the arg dictionary.

pt - the pivot table object 
datacells - the datacells object of the primary pivot table
labels - the row or column labels object corresponding to the DIMENSION setting
ncells - the number of rows or columns in the datacells object.  I.e., if DIMENSION
is columns, it is the number or rows.
roworcol - the current row or column in the table.
Two entries initially.  These are solely for use by the user
function and have no effect on operation of this command.
"firstload" - True.
"firsttable" - set to True each time a new table is evaluated.
It is up to the user code to set these to False appropriately.
Additional user values can be preserved between calls by saving them in arg.

For secondary tables,
ncells2 - the number of rows or columns in the secondary table data cells
sdatacells - the secondary data cells object
resultnumber - the number starting at zero of the target location
Columns or row locations are sequenced in the order they are 
specified in the LOCATION keyword.

In this example the formula specifies get a call to the custom function, but it
can be combined with other value constructs.

Additional arguments can be supplied to the custom function in the style of the first
example.  If the formula specifies
FORMULA = "customexample.usesecondary(arg, fred=100)".
Then the function would be declared as
usesecondary(arg, fred)
and the value of fred would be 100 when the function is called.
"""
def Run(args):
    """Execute the STATS TABLE CALC extension command"""

    args = args[list(args.keys())[0]]

    oobj = Syntax([
        Template("SUBTYPE", subc="",  ktype="str", var="subtype", islist=True),
        Template("PROCESS", subc="", ktype="str", var="process", islist=False),
        Template("PRINTLABELS", subc="", ktype="bool", var="printlabels"),
        Template("NEXTSUBTYPE", subc="", ktype="str", var="nextsubtype", islist=False),
        Template("PREVSUBTYPE", subc="", ktype="str", var="prevsubtype", islist=False),
        
        Template("DIMENSION", subc="TARGET", ktype="str", var="dimension", vallist=["columns","rows"]),
        Template("LEVEL", subc="TARGET", ktype="int", var= "level"),
        Template("LOCATION", subc="TARGET", ktype="literal", var="location", islist=True),
        Template("REPEATLOC", subc="TARGET", ktype="bool", var="repeatloc"),
        Template("LABEL", subc="TARGET", ktype="literal", var="targetlabel"),
        Template("MODE", subc="TARGET", ktype="str", var="mode", vallist=["replace", "before", "after"]),
        Template("FORMULA", subc="TARGET", ktype="literal", var="formula"),
        Template("CUSTOMMODULE", subc="TARGET", ktype="literal", var="custommodule"),
        Template("HIDEINPUTS", subc="TARGET", ktype="bool", var="hide", islist=False),

        Template("WIDTH", subc="FORMAT", ktype="int", var="width", vallist=(0,), islist=False),
        Template("CELLFORMAT", subc="FORMAT", ktype="literal", var="cellformat"),
        Template("DECIMALS", subc="FORMAT", ktype="int", var="decimals", vallist=(0,)),
        Template("INVALID", subc="FORMAT", ktype="literal", var="floatfail"),
        Template("ALIGN", subc="FORMAT", ktype="str", var="align", 
            vallist=["asis", "lefttop", "center", "rightbottom"]),
        Template("HELP", subc="", ktype="bool")])

    # A HELP subcommand overrides all else
    if "HELP" in args:
        #print helptext
        helper()
    else:
        processcmd(oobj, args, modifyvalues.modify)

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print("Help file not found:" + helpspec)
try:    #override
    from extension import helper
except:
    pass