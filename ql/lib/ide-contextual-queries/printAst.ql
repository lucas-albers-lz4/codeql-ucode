/**
 * @name Print AST
 * @description Produces a representation of a file's Abstract Syntax Tree.
 *              M1 uses the generated TreeSitter nodes (wrapper AST.qll is not imported).
 * @id ucode/print-ast
 * @kind problem
 * @problem.severity recommendation
 * @tags ide-contextual-queries/print-ast
 */

import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter

from UCODE::AstNode n
where n.getLocation().getFile().getBaseName() = "luci"
select n, n.getAPrimaryQlClass()
