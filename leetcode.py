# def combine(n: int, k: int):
#     result = []
#
#     def backtrack(start: int, current: list[int]):
#         # Если набрали k чисел — сохраняем комбинацию
#         if len(current) == k:
#             result.append(current[:])  # копия
#             return
#         # Перебираем возможные следующие числа
#         for i in range(start, n + 1):
#             current.append(i)  # выбираем число
#             backtrack(i + 1, current)  # рекурсивно добавляем следующие
#             current.pop()  # возврат (откатываем выбор)
#
#     backtrack(1, [])
#     return result
#
#
# print(combine(n=5, k=2))
from pickletools import string1


# def permutations(nums):
#     result = []
#     n = len(nums)
#
#     def backtrack(current):
#         if len(current) == n:
#             result.append(current[:])
#             return
#
#         for i in range(n):
#             if nums[i] in current:  # пропускаем уже взятые
#                 continue
#             current.append(nums[i])
#             backtrack(current)
#             current.pop()
#
#     backtrack([])
#     return result
#
#
# print(permutations([1, 2, 3]))


from collections import defaultdict
from typing import Mapping


country_codes = ["754", "690", "450", "479"]  # Канада, Китай, Япония, Шри-Ланка

products = [
    "4506436054267",
    "7547682958186",
    "6900626469201",
    "7543817559796",
    "7544194259711",
    "6900590565047",
    "6901237511586",
    "4502714135954",
    "4500295752923",
]


def name_that_have_sense() -> dict[str, set]:
    d = defaultdict(set)
    for i, product in enumerate(products):
        if int(product[0]) == 4:
            d[country_codes[0]].add(product)
            continue
        if int(product[0]) == 6:
            d[country_codes[1]].add(product)
            continue
        if int(product[0]) == 7:
            d[country_codes[2]].add(product)
            continue
    return d


print(name_that_have_sense())
