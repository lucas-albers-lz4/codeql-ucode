import codeql.Locations
import codeql.files.FileSystem
import codeql.ucode.Diagnostics
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.m3.Models
import codeql.ucode.AST

// Wrapper AST is imported so CFG/SSA construction can see AstNode/Stmts/Expr.
// CFG is importable as codeql.ucode.CFG and SSA/dataflow as codeql.ucode.DataFlow.
// Neither is re-exported here. Production LocalTaint / RequestArgsExec stay on
// Models. SsaReachesSystem.ql imports DataFlow additively; that is not
// setInitAction path_found and does not resolve imported luci.sys callees.
