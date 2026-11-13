import codeql.Locations
import codeql.files.FileSystem
import codeql.ucode.Diagnostics
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.m3.Models
import codeql.ucode.AST

// Wrapper AST is imported so CFG/SSA construction can see AstNode/Stmts/Expr.
// CFG is importable as codeql.ucode.CFG and SSA/dataflow as codeql.ucode.DataFlow.
// Neither is re-exported here. Production LocalTaint / RequestArgsExec stay on
// Models. SsaReachesSystem.ql imports DataFlow additively and uses ordered
// expression and SSA definition/read nodes. That is not setInitAction
// path_found. viableSourceCallable resolves unique same-file identifier
// and member-property FunctionDeclarations; imported luci.sys callees
// remain unresolved / inconclusive. viableLibraryCallable resolves
// builtin identifier system and imported fs popen / basename /
// access / open / readfile; luci.sys stays unresolved.
// jumpStep uses identifier simpleIdentifierCall and unique same-file
// member FunctionDeclarations.
