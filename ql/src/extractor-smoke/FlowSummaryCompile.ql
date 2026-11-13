/**
 * @name FlowSummary and Concepts compile smoke
 * @description Typecheck FlowSummary, FlowSource, FlowSink, ModelsAsData, and
 *              Concepts. Import smoke only. Not production taint and not
 *              setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/flow-summary-compile
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.dataflow.FlowSummary
import codeql.ucode.dataflow.FlowSource
import codeql.ucode.dataflow.FlowSink
private import codeql.ucode.dataflow.internal.ModelsAsData
import codeql.ucode.Concepts

from File f
where
  none() and
  not exists(SummarizedCallable sc) and
  not exists(FlowSource src) and
  not exists(FlowSink snk) and
  not exists(ActiveThreatModelSource tm) and
  not exists(QlBuiltins::ExtensionId id, string model | interpretModelForTest(id, model))
select f, "flow-summary compile"
