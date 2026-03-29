创建一个新的算子。

参数：$ARGUMENTS（算子名称和功能描述）

步骤：
1. 读取 engine/algos/algo_base.py 了解 Algo 基类接口
2. 参考现有算子（如 algos_select.py、algos_weight.py）的实现模式
3. 在 engine/algos/ 下创建或编辑对应文件
4. 实现 __call__(self, target) 方法
5. 确保算子能通过 target.temp 与其他算子交互
6. 给出使用示例
