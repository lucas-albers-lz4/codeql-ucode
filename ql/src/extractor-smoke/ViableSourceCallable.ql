/**
 * @name Same-file identifier FunctionDeclaration call targets
 * @description Reports viableCallable targets for unique same-file
 *              identifier calls to FunctionDeclarations. Testing only.
 *              Imported luci.sys stays unresolved. Not argument-to-
 *              parameter taint, not production taint, and not
 *              setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/viable-source-callable
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
private import codeql.ucode.dataflow.internal.DataFlowDispatch

from DataFlowCall call, DataFlowCallable tgt, string name, File f
where
  tgt = viableCallable(call) and
  exists(tgt.asCfgScope()) and
  name = call.asCall().getCall().getIdentifier().getName() and
  name != "" and
  f = call.getLocation().getFile() and
  (
    f.getBaseName() = "luci" or
    f.getBaseName() = "ssa_pos" or
    f.getBaseName() = "sys.uc"
  )
select call, name + " in " + f.getBaseName()
