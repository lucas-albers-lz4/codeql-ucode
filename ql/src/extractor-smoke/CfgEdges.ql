/**
 * @name CFG successor edges
 * @description Successor edges from the wrapper CFG. Testing only; not a
 *              production taint query.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/cfg-edges
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.CFG
import codeql.ucode.controlflow.CfgNodes

from AstCfgNode pred, CfgNode succ, SuccessorType t, string eq, string kind
where
  pred.getASuccessor(t) = succ and
  (if pred.getScope() = succ.getScope() then eq = "1" else eq = "0") and
  (if succ instanceof AstCfgNode then kind = "ast" else kind = "exit")
select pred,
  pred.getFile().getBaseName() + ":" + pred.getLocation().getStartLine().toString() + " -> " +
    succ.getFile().getBaseName() + ":" + succ.getLocation().getStartLine().toString() +
    " scopeEq=" + eq + " scopeLine=" + pred.getScope().getLocation().getStartLine().toString() +
    " kind=" + kind + " type=" + t.toString()
