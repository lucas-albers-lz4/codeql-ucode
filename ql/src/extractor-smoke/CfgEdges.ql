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

from CfgNode pred, CfgNode succ, string eq
where
  pred.getASuccessor() = succ and
  (
    pred.getScope() = succ.getScope() and eq = "1"
    or
    not pred.getScope() = succ.getScope() and eq = "0"
  )
select pred,
  pred.getFile().getBaseName() + " -> " + succ.getFile().getBaseName() + " scopeEq=" + eq
