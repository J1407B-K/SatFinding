def stats(y):
 n=len(y); m=sum(y)/n; var=sum((x-m)**2 for x in y)/n; xm=(n-1)/2; den=sum((i-xm)**2 for i in range(n)); sl=sum((i-xm)*(x-m) for i,x in enumerate(y))/den if den else 0.; return m,var,sl
