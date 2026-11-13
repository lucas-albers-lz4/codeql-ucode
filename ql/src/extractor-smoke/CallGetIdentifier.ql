/**
 * @name Call.getIdentifier from extracted function identifiers
 * @description Reports wrapper Call.getIdentifier when the extracted
 *              function field is already an identifier. Testing only.
 *              Not ParameterNode, not argument-to-parameter flow, not
 *              production taint, and not setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/call-get-identifier
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.ast.Idents

from Call c, Idents ident, string name
where
  ident = c.getIdentifier() and
  name = ident.getName() and
  name != "" and
  not exists(Call other | exists(other.getArguments())) and
  (ident.getFile().getBaseName() = "luci" or ident.getFile().getBaseName() = "ssa_pos")
select ident, name + " in " + ident.getFile().getBaseName()
