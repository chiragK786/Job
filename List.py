c = [0,1, 2, 3, 4, 5, 6]

print(c[0:])
print(c[2:4])
print(c[:4])
y = len(c)-1
print(c[y])


s = "Pradeep"
print(list(s)) # ONly String


#Dictionary

d1 = {
    'name' : "Chirag",
    'Org' :"SQB"

}


print(d1.get('name'))
d1['test'] = "good"
print(d1)
print(d1.keys())





"""

1. Tuple is same as per List but it is immutable

"""

t2 = ('1','2',2,45,4.5)
print(t2)
print(type(t2))



s1 = {'Jai', "ho", "Jai"}


print(s1)
print(type(s1))
