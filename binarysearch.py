
def binary(arr,ele):
    start = 0
    end = len(arr)-1

    while start<=end:
        mid = (start + end) // 2
        if arr[mid] == ele:
            return mid
        elif arr[mid] > ele:
            end = mid - 1
        else:
            start = mid + 1

    return -1


ar = [3,45,56,77,88,99,100]
t = 3
index = binary(ar,t)
print(index)
