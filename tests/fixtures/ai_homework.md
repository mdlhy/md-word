# 数据结构课程作业

## 题目一：链表反转

请实现一个函数，反转单链表：

```python
def reverse_list(head):
    prev = None
    current = head
    while current:
        next_node = current.next
        current.next = prev
        prev = current
        current = next_node
    return prev
```

时间复杂度为$O(n)$，空间复杂度为$O(1)$。

## 题目二：二叉树遍历

- 前序遍历：根→左→右
- 中序遍历：左→根→右
- 后序遍历：左→右→根

> 提示：可以使用递归或迭代方法实现

| 遍历方式 | 递归 | 迭代 |
|----------|------|------|
| 前序 | 简单 | 中等 |
| 中序 | 简单 | 困难 |
| 后序 | 简单 | 囃难 |
