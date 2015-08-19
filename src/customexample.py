#Licensed Materials - Property of IBM
#IBM SPSS Products: Statistics General
#(c) Copyright IBM Corp. 2014
#US Government Users Restricted Rights - Use, duplication or disclosure 
#restricted by GSA ADP Schedule Contract with IBM Corp.

# Example custom functions for use with STATS TABLE CALC

def custom(datacells, ncells, value):
  """Calculate percent of total"""
  
  x = float(datacells.GetUnformattedValueAt(ncells-1,2))  # total
  return  float(value) / x

def custom2(value, arg):
  return 100

def usesecondary(arg):
  return arg['sdatacells'].GetValueAt(arg['roworcol'], arg['resultnumber'])

def usesecondary2(arg, fred):
  return arg['sdatacells'].GetValueAt(arg['roworcol'], arg['resultnumber'])

#CTABLES
  #/VLABELS VARIABLES=jobcat minority DISPLAY=DEFAULT
  #/TABLE jobcat [COUNT F40.0] BY minority
  #STATS TABLE CALC SUBTYPE="'Custom Table'" PROCESS=PRECEDING 
  #/TARGET FORMULA="customexample.rowdiff(datacells, roworcol)" 
      #CUSTOMMODULE="customexample"
      #DIMENSION=COLUMNS LEVEL = -1  LOCATION=1 REPEATLOC=NO LABEL="Difference" MODE=AFTER.  

def rowdiff(datacells, roworcol):
  return float(datacells.GetUnformattedValueAt(roworcol, 0)) - float(datacells.GetUnformattedValueAt(roworcol-1, 0))

# Using the current target row or column number in a custom function
#CTABLES /TABLE jobcat [COUNT F40.0] BY minority.

#STATS TABLE CALC SUBTYPE="'Custom Table'" PROCESS=PRECEDING 
#/TARGET FORMULA="customexample.rowdiffloc(datacells, roworcol, currentloc)" 
#CUSTOMMODULE="customexample"
#DIMENSION=COLUMNS LEVEL = -1  LOCATION=1 REPEATLOC=NO LABEL="Difference" MODE=AFTER.

def rowdiffloc(datacells, roworcol, currentloc):
  return float(datacells.GetUnformattedValueAt(roworcol, int(currentloc))) - float(datacells.GetUnformattedValueAt(roworcol-1, int(currentloc)))

# Example: replace row totals column of a custom table in pct
# with the count:

#CTABLES 
  #/TABLE educ [colPCT.COUNT PCT40.1, TOTALS[COUNT F40.0]] BY jobcat 
  #/SLABELS POSITION=ROW 
  #/CATEGORIES VARIABLES=educ jobcat TOTAL=YES POSITION=AFTER.

#STATS TABLE CALC SUBTYPE="customtable" 
#/TARGET DIMENSION=COLUMNS
    #LOCATION=-1 REPEATLOC=NO LABEL="Total" MODE=REPLACE
    #CUSTOMMODULE="customexample"
    #FORMULA="customexample.rowPctToCount(datacells,  ncells, roworcol)"
#/FORMAT CELLFORMAT="asis"  INVALID="".


def rowPctToCount(datacells, ncells, roworcol):
  
  lastcol = datacells.GetNumColumns() - 1
  pct = float(datacells.GetUnformattedValueAt(roworcol, lastcol))
  if roworcol == ncells-1:
    return pct
  base = float(datacells.GetUnformattedValueAt(ncells-1, lastcol))
  return round(pct * base / 100.)
