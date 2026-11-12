import codeql.Locations
import codeql.files.FileSystem
import codeql.ucode.Diagnostics
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.m3.Models
import codeql.ucode.AST

// Wrapper AST is imported so CFG/SSA construction can see AstNode/Stmts/Expr.
// CFG is importable as codeql.ucode.CFG and SSA/dataflow as codeql.ucode.DataFlow.
// Neither is re-exported here: production M3/M4 queries stay on Models until
// their own smokes prove the library. Do not treat this as setInitAction path_found.
