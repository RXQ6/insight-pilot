# LangGraph 文档 PR（复制即用）

> 目标：在 LangGraph 官方文档的 Reducers 章节加一小节 "Resetting a reducer field"。
> 文档 PR 是新人最容易过的贡献：不涉及代码评审深度，解决的是真实困惑（你的 Issue 就是证据）。

## 找源文件（30 秒）

1. 打开 https://github.com/langchain-ai/langgraph
2. 在仓库搜索框搜 `low_level.md`（Reducers 章节所在文件）
3. 进入文件后，找到 Reducers 小节（搜索页面内 `### Reducers`）

## 网页编辑提交（不需要本地 git）

1. 文件右上角点 ✏️（编辑按钮，GitHub 会自动 fork 到你的账号）
2. 在 Reducers 章节末尾（该节最后一个代码块之后）插入下面的内容
3. 页面底部填提交说明 → **Commit changes** → GitHub 会引导你 **Create pull request**
4. PR 标题：`docs: add "Resetting a reducer field" to Reducers section`

## 要插入的文档内容（英文，直接复制）

```markdown
### Resetting a reducer field

A common confusion with reducer fields: with `Annotated[list, operator.add]`, returning `[]` from a node does **not** clear the field. Reducer semantics merge the returned value into the current one (`reducer(current, new)`), so `[]` is appended to the existing list and previous values are kept:

```python
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph

class State(TypedDict):
    errors: Annotated[list, operator.add]

# node A returns {"errors": ["bad sql"]}
# node B returns {"errors": []}   # state["errors"] is still ["bad sql"]
```

To allow a node to reset (clear) a reducer-managed field, use a custom reducer that replaces the value instead of merging:

```python
def overwrite(current: list, new: list) -> list:
    return new

class State(TypedDict):
    messages: Annotated[list, operator.add]
    errors: Annotated[list, overwrite]   # node can now clear with {"errors": []}
```

This pattern is useful for error buffers or retry counters that must be cleared between retry attempts.
```

注意：粘贴时把三个 ```python 代码块前的反引号保留完整（上面用四个反引号包裹是为了让你能复制，实际插入时用三个反引号）。

## 如果 PR 被要求修改

维护者可能提意见（比如措辞、示例简化）。把评论截图或原文发我，我帮你改好再提。

## 时间线建议（不干等）

| 时间 | 动作 |
|---|---|
| 今天 | 提文档 PR；跑评测（`run_eval.py`）；把评测报告发我 |
| 24-48h | 看 Issue 和 PR 有没有回复；有回复贴给我，我帮你起草回复 |
| 3 天内 | 写博客《LangGraph 踩坑：operator.add 的 errors 为什么清不掉》（素材见 `docs/langgraph-issue-draft.md` 末尾） |
| 随时 | `git push origin main`（你本地）→ CI 三端全绿 |
