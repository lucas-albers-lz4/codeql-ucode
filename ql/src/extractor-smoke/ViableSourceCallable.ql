/**
 * @name Same-file FunctionDeclaration and builtin system call targets
 * @description Reports viableCallable targets for unique same-file
 *              identifier and member-property FunctionDeclarations,
 *              plus builtin identifier system as a library callable.
 *              Testing only. Imported luci.sys / popen / basename /
 *              fd.read stay unresolved. Not argument-to-parameter
 *              taint, not production taint, and not setInitAction
 *              path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/viable-source-callable
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
private import codeql.ucode.dataflow.internal.DataFlowDispatch

from DataFlowCall call, DataFlowCallable tgt, string name, File f, string label
where
  tgt = viableCallable(call) and
  name = sourceCallName(call) and
  name != "" and
  f = call.getLocation().getFile() and
  (
    f.getBaseName() = "luci" or
    f.getBaseName() = "ssa_pos" or
    f.getBaseName() = "sys.uc"
  ) and
  (
    exists(tgt.asCfgScope()) and
    label = name + " in " + f.getBaseName()
    or
    exists(string lib |
      lib = tgt.asLibraryCallable() and
      label = "library " + lib + " in " + f.getBaseName()
    )
  )
select call, label
