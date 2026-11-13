/**
 * @name FlowSummary getACall for identifier callees
 * @description Reports FlowSummary getACall when Call.getIdentifier
 *              matches a summarized callable name. Member callees have
 *              no identifier and are not returned. Testing only. Not
 *              production taint, not localFlowStep, and not
 *              setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/get-a-call
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.dataflow.FlowSummary
private import codeql.ucode.dataflow.internal.FlowSummaryImpl
private import codeql.ucode.dataflow.internal.DataFlowDispatch

from CallExpression c, SummarizedCallable sc, DataFlowCall dfc, string label
where
  dfc = IdentifierCalls::getACall(sc) and
  c = dfc.asCall().getCall() and
  (c.getFile().getBaseName() = "luci" or c.getFile().getBaseName() = "ssa_pos") and
  not exists(string arg | Input::encodeContent(_, arg) = "Future") and
  (
    exists(string name |
      name = c.getIdentifier().getName() and
      name = sc and
      label = name
    )
    or
    not exists(c.getIdentifier()) and
    label = "member"
  )
select c, label + " in " + c.getFile().getBaseName()
