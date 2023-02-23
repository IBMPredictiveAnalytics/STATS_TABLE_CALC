import math

def d(arg):
    datacells = arg["datacells"]
    roworcol = arg["roworcol"]
    """Compute Cohen's d statistic from the Group Statistics table
    
    datacells is the data in the Group Statistics pivot table
    roworcol is the current row or column being processed
    d is adjusted for bias per Grissom and Kim"""
    
    if roworcol > 0:  # Only display in first row
        return ""
    sd1 = float(datacells.GetUnformattedValueAt(0, 2))
    sd2 = float(datacells.GetUnformattedValueAt(1,2))
    mean1 = float(datacells.GetUnformattedValueAt(0,1))
    mean2 = float(datacells.GetUnformattedValueAt(1,1))
    n1 = float(datacells.GetUnformattedValueAt(0,0))
    n2 = float(datacells.GetUnformattedValueAt(1,0))
    
    pooledsd = math.sqrt(((n1-1) * sd1**2 + (n2-1) * sd2**2) / (n1+n2))
    d = (mean1 - mean2) / pooledsd
    # Apply Hedges & Olkin bias adjustment
    dadj = d * (1 - 3 / (4 * (n1 + n2 - 2) - 1))
    return dadj

