from numpy import average
import pandas
import sys
import os
df = pandas.read_csv(os.path.join(sys.argv[1],'times'), header='infer')
print(average(df.iloc[:,1]))
