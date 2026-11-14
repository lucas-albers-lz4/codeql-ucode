/**
 * @name Experimental system callable binding control
 * @description Reports experimental library system targets at each call site.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/system-library-binding
 * @tags testing
 */

import codeql.ucode.AST
private import codeql.ucode.dataflow.internal.DataFlowDispatch

from DataFlowCall call, DataFlowCallable target
where target = viableCallable(call) and target.asLibraryCallable() = "system"
select call, call.getLocation().getStartLine().toString()
