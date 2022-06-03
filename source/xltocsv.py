import pandas

data = pandas.read_excel("./data/my5yielddata2010-current.xlsx")
data.to_csv("./data/my5yielddata2010-current.csv")