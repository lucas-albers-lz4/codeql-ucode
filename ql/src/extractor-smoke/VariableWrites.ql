/**
 * @name VariableWriteAccess identifiers
 * @description Identifier assignment/update writes. Testing only; not a
 *              production taint query and not setInitAction path_found.
 *              Lexical declarators are not VariableWriteAccess.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/variable-writes
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST

from VariableWriteAccess wa, File f
where
  f = wa.getLocation().getFile() and
  (f.getBaseName() = "ssa_pos" or f.getBaseName() = "ssa_neg")
select wa,
  wa.getName() + ":" + wa.getLocation().getStartLine().toString() + " in " + f.getBaseName()
