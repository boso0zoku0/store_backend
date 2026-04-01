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


def permutations(nums):
    result = []
    n = len(nums)

    def backtrack(current):
        if len(current) == n:
            result.append(current[:])
            return

        for i in range(n):
            if nums[i] in current:  # пропускаем уже взятые
                continue
            current.append(nums[i])
            backtrack(current)
            current.pop()

    backtrack([])
    return result


print(permutations([1, 2, 3]))
