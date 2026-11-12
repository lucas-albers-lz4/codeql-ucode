/**
 * @name Print luci AST nodes
 * @description M1 gate: at least one AST node whose file basename is luci.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/print-luci-ast
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter

from UCODE::AstNode n
where n.getLocation().getFile().getBaseName() = "luci"
select n, n.getAPrimaryQlClass()
