# LangGraph Issue 提交流程（复制即用）

> 目标：向 langchain-ai/langgraph 提交一个"踩坑澄清" Issue，确认后跟进文档 PR。
> 发之前先在仓库搜一遍有没有重复：https://github.com/langchain-ai/langgraph/issues?q=clear+reducer+field

## 操作步骤（约 1 分钟）

1. 打开 https://github.com/langchain-ai/langgraph/issues/new
2. 标题填：`Returning [] with Annotated[list, operator.add] does not clear the field — how to reset a reducer field?`
3. 正文粘贴下面的 Issue 草稿（英文，替换 [版本号]）
4. 点 Submit new issue

## Issue 草稿（复制下面的全部内容）

```markdown
**Title:** Returning `[]` with `Annotated[list, operator.add]` does not clear the field — how to reset a reducer field?

**Body:**

Hi! I'm building a StateGraph with `errors: Annotated[list, operator.add]`. A node returns `{"errors": []}` expecting to clear accumulated errors, but the field keeps its previous value:

```python
from typing import Annotated, TypedDict
import operator
from langgraph.graph import StateGraph

class State(TypedDict):
    errors: Annotated[list, operator.add]

# node A returns {"errors": ["bad sql"]}
# node B returns {"errors": []}          # state["errors"] stays ["bad sql"]
```

I understand this is because reducer semantics merge returned values via `reducer(current, new)`, so `[]` is appended rather than replacing the field.

This tripped me up and caused an infinite reflect -> retry loop in my agent (agent_step failed -> reflect tried to clear errors but couldn't -> route kept going back to reflect) until I hit the graph recursion limit.

**Suggestion:** the Reducers docs (https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers) don't mention how to *reset/clear* a reducer-managed field. A short section like "Resetting a reducer field" (custom reducer that replaces the value, or removal semantics) would save a lot of confusion. Happy to open a docs PR if that's welcome.

**Env:** langgraph [版本号如 0.2.x], python [版本号如 3.12]
```

## 提交后跟进

- 维护者回复后，如果表示欢迎文档 PR → 回来找我，我给你写 LangGraph 文档 PR 的完整改动（Reducers 章节加 "Resetting a reducer field" 小节）
- 如果被关掉（说 works as intended）→ 没关系，Issue 本身已经记录在案；重点是博客和面试，不是这个 Issue 的成败

## 本地怎么查版本号

```powershell
cd D:\insight-pilot\agent
.venv\Scripts\python -c "import langgraph; print(langgraph.__version__)"
```

## 这个坑的完整故事（博客/面试用）

**现象**：agent 在 reflect 纠错循环里死循环到 recursion limit。
**定位**：`Annotated[list, operator.add]` 是 reducer 累加语义——节点返回 `[]` 相当于把空列表"加进"现有列表，字段清不掉；于是 `reflect` 永远清不掉 `errors`，路由永远回到 `reflect`。
**修复**（已提交 `7510aa5`）：① `errors` 改为普通覆盖字段；② 路由 `route_after_agent` 优先检查 `final_answer`（有答案直接收尾）；③ 超步数分支显式清空 errors；④ 评测脚本捕获 `GraphRecursionError` 兜底。
**教训**：框架的 reducer 语义（`reducer(current, new)`）和直觉相反——"返回空值清空"在 reducer 字段上不成立。
