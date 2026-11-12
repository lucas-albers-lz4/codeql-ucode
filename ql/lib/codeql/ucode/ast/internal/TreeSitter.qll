/**
 * CodeQL library for UCODE
 * Automatically generated from the tree-sitter grammar; do not edit
 */

import codeql.Locations as L

module UCODE {
  /** The base class for all AST nodes */
  class AstNode extends @ucode_ast_node {
    /** Gets a string representation of this element. */
    string toString() { result = this.getAPrimaryQlClass() }

    /** Gets the location of this element. */
    final L::Location getLocation() { ucode_ast_node_location(this, result) }

    /** Gets the parent of this element. */
    final AstNode getParent() { ucode_ast_node_parent(this, result, _) }

    /** Gets the index of this node among the children of its parent. */
    final int getParentIndex() { ucode_ast_node_parent(this, _, result) }

    /** Gets a field or child node of this node. */
    AstNode getAFieldOrChild() { none() }

    /** Gets the name of the primary QL class for this element. */
    string getAPrimaryQlClass() { result = "???" }

    /** Gets a comma-separated list of the names of the primary CodeQL classes to which this element belongs. */
    string getPrimaryQlClasses() { result = concat(this.getAPrimaryQlClass(), ",") }
  }

  /** A token. */
  class Token extends @ucode_token, AstNode {
    /** Gets the value of this token. */
    final string getValue() { ucode_tokeninfo(this, _, result) }

    /** Gets a string representation of this element. */
    final override string toString() { result = this.getValue() }

    /** Gets the name of the primary QL class for this element. */
    override string getAPrimaryQlClass() { result = "Token" }
  }

  /** A reserved word. */
  class ReservedWord extends @ucode_reserved_word, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ReservedWord" }
  }

  /** A class representing `arguments` nodes. */
  class Arguments extends @ucode_arguments, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Arguments" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { ucode_arguments_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_arguments_child(this, _, result) }
  }

  /** A class representing `array` nodes. */
  class Array extends @ucode_array, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Array" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { ucode_array_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_array_child(this, _, result) }
  }

  /** A class representing `arrow_function` nodes. */
  class ArrowFunction extends @ucode_arrow_function, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ArrowFunction" }

    /** Gets the node corresponding to the field `body`. */
    final AstNode getBody() { ucode_arrow_function_def(this, result) }

    /** Gets the node corresponding to the field `parameter`. */
    final Identifier getParameter() { ucode_arrow_function_parameter(this, result) }

    /** Gets the node corresponding to the field `parameters`. */
    final FormalParameters getParameters() { ucode_arrow_function_parameters(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_arrow_function_def(this, result) or
      ucode_arrow_function_parameter(this, result) or
      ucode_arrow_function_parameters(this, result)
    }
  }

  /** A class representing `assignment_expression` nodes. */
  class AssignmentExpression extends @ucode_assignment_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "AssignmentExpression" }

    /** Gets the node corresponding to the field `left`. */
    final AstNode getLeft() { ucode_assignment_expression_def(this, result, _) }

    /** Gets the node corresponding to the field `right`. */
    final Expression getRight() { ucode_assignment_expression_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_assignment_expression_def(this, result, _) or
      ucode_assignment_expression_def(this, _, result)
    }
  }

  /** A class representing `augmented_assignment_expression` nodes. */
  class AugmentedAssignmentExpression extends @ucode_augmented_assignment_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "AugmentedAssignmentExpression" }

    /** Gets the node corresponding to the field `left`. */
    final AstNode getLeft() { ucode_augmented_assignment_expression_def(this, result, _, _) }

    /** Gets the node corresponding to the field `operator`. */
    final string getOperator() {
      exists(int value | ucode_augmented_assignment_expression_def(this, _, value, _) |
        result = "%=" and value = 0
        or
        result = "&&=" and value = 1
        or
        result = "&=" and value = 2
        or
        result = "**=" and value = 3
        or
        result = "*=" and value = 4
        or
        result = "+=" and value = 5
        or
        result = "-=" and value = 6
        or
        result = "/=" and value = 7
        or
        result = "<<=" and value = 8
        or
        result = ">>=" and value = 9
        or
        result = "??=" and value = 10
        or
        result = "^=" and value = 11
        or
        result = "|=" and value = 12
        or
        result = "||=" and value = 13
      )
    }

    /** Gets the node corresponding to the field `right`. */
    final Expression getRight() { ucode_augmented_assignment_expression_def(this, _, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_augmented_assignment_expression_def(this, result, _, _) or
      ucode_augmented_assignment_expression_def(this, _, _, result)
    }
  }

  /** A class representing `binary_expression` nodes. */
  class BinaryExpression extends @ucode_binary_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "BinaryExpression" }

    /** Gets the node corresponding to the field `left`. */
    final Expression getLeft() { ucode_binary_expression_def(this, result, _, _) }

    /** Gets the node corresponding to the field `operator`. */
    final string getOperator() {
      exists(int value | ucode_binary_expression_def(this, _, value, _) |
        result = "!=" and value = 0
        or
        result = "!==" and value = 1
        or
        result = "%" and value = 2
        or
        result = "&" and value = 3
        or
        result = "&&" and value = 4
        or
        result = "*" and value = 5
        or
        result = "**" and value = 6
        or
        result = "+" and value = 7
        or
        result = "-" and value = 8
        or
        result = "/" and value = 9
        or
        result = "<" and value = 10
        or
        result = "<<" and value = 11
        or
        result = "<=" and value = 12
        or
        result = "==" and value = 13
        or
        result = "===" and value = 14
        or
        result = ">" and value = 15
        or
        result = ">=" and value = 16
        or
        result = ">>" and value = 17
        or
        result = "??" and value = 18
        or
        result = "^" and value = 19
        or
        result = "in" and value = 20
        or
        result = "|" and value = 21
        or
        result = "||" and value = 22
      )
    }

    /** Gets the node corresponding to the field `right`. */
    final Expression getRight() { ucode_binary_expression_def(this, _, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_binary_expression_def(this, result, _, _) or
      ucode_binary_expression_def(this, _, _, result)
    }
  }

  /** A class representing `break_statement` tokens. */
  class BreakStatement extends @ucode_token_break_statement, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "BreakStatement" }
  }

  /** A class representing `call_expression` nodes. */
  class CallExpression extends @ucode_call_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "CallExpression" }

    /** Gets the node corresponding to the field `arguments`. */
    final Arguments getArguments() { ucode_call_expression_def(this, result, _) }

    /** Gets the node corresponding to the field `function`. */
    final Expression getFunction() { ucode_call_expression_def(this, _, result) }

    /** Gets the node corresponding to the field `optional_chain`. */
    final OptionalChain getOptionalChain() { ucode_call_expression_optional_chain(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_call_expression_def(this, result, _) or
      ucode_call_expression_def(this, _, result) or
      ucode_call_expression_optional_chain(this, result)
    }
  }

  /** A class representing `catch_clause` nodes. */
  class CatchClause extends @ucode_catch_clause, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "CatchClause" }

    /** Gets the node corresponding to the field `body`. */
    final StatementBlock getBody() { ucode_catch_clause_def(this, result) }

    /** Gets the node corresponding to the field `parameter`. */
    final Identifier getParameter() { ucode_catch_clause_parameter(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_catch_clause_def(this, result) or ucode_catch_clause_parameter(this, result)
    }
  }

  /** A class representing `comment` tokens. */
  class Comment extends @ucode_token_comment, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Comment" }
  }

  /** A class representing `computed_property_name` nodes. */
  class ComputedPropertyName extends @ucode_computed_property_name, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ComputedPropertyName" }

    /** Gets the child of this node. */
    final Expression getChild() { ucode_computed_property_name_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_computed_property_name_def(this, result) }
  }

  /** A class representing `continue_statement` tokens. */
  class ContinueStatement extends @ucode_token_continue_statement, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ContinueStatement" }
  }

  class Declaration extends @ucode_declaration, AstNode { }

  /** A class representing `default` tokens. */
  class Default extends @ucode_token_default, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Default" }
  }

  /** A class representing `delete_expression` nodes. */
  class DeleteExpression extends @ucode_delete_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "DeleteExpression" }

    /** Gets the node corresponding to the field `argument`. */
    final AstNode getArgument() { ucode_delete_expression_def(this, result, _) }

    /** Gets the node corresponding to the field `operator`. */
    final string getOperator() {
      exists(int value | ucode_delete_expression_def(this, _, value) |
        (result = "delete" and value = 0)
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_delete_expression_def(this, result, _) }
  }

  /** A class representing `doc_comment` tokens. */
  class DocComment extends @ucode_token_doc_comment, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "DocComment" }
  }

  /** A class representing `elif_clause` nodes. */
  class ElifClause extends @ucode_elif_clause, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ElifClause" }

    /** Gets the node corresponding to the field `condition`. */
    final ParenthesizedExpression getCondition() { ucode_elif_clause_def(this, result) }

    /** Gets the node corresponding to the field `consequence`. */
    final StatementList getConsequence() { ucode_elif_clause_consequence(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_elif_clause_def(this, result) or ucode_elif_clause_consequence(this, result)
    }
  }

  /** A class representing `else_alt_clause` nodes. */
  class ElseAltClause extends @ucode_else_alt_clause, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ElseAltClause" }

    /** Gets the child of this node. */
    final StatementList getChild() { ucode_else_alt_clause_child(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_else_alt_clause_child(this, result) }
  }

  /** A class representing `else_clause` nodes. */
  class ElseClause extends @ucode_else_clause, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ElseClause" }

    /** Gets the child of this node. */
    final AstNode getChild() { ucode_else_clause_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_else_clause_def(this, result) }
  }

  /** A class representing `empty_statement` tokens. */
  class EmptyStatement extends @ucode_token_empty_statement, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "EmptyStatement" }
  }

  /** A class representing `escape_sequence` tokens. */
  class EscapeSequence extends @ucode_token_escape_sequence, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "EscapeSequence" }
  }

  /** A class representing `export_clause` nodes. */
  class ExportClause extends @ucode_export_clause, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ExportClause" }

    /** Gets the `i`th child of this node. */
    final ExportSpecifier getChild(int i) { ucode_export_clause_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_export_clause_child(this, _, result) }
  }

  /** A class representing `export_specifier` nodes. */
  class ExportSpecifier extends @ucode_export_specifier, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ExportSpecifier" }

    /** Gets the node corresponding to the field `alias`. */
    final AstNode getAlias() { ucode_export_specifier_alias(this, result) }

    /** Gets the node corresponding to the field `name`. */
    final AstNode getName() { ucode_export_specifier_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_export_specifier_alias(this, result) or ucode_export_specifier_def(this, result)
    }
  }

  /** A class representing `export_statement` nodes. */
  class ExportStatement extends @ucode_export_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ExportStatement" }

    /** Gets the node corresponding to the field `clause`. */
    final ExportClause getClause() { ucode_export_statement_clause(this, result) }

    /** Gets the node corresponding to the field `declaration`. */
    final AstNode getDeclaration() { ucode_export_statement_declaration(this, result) }

    /** Gets the node corresponding to the field `value`. */
    final Expression getValue() { ucode_export_statement_value(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_export_statement_clause(this, result) or
      ucode_export_statement_declaration(this, result) or
      ucode_export_statement_value(this, result)
    }
  }

  class Expression extends @ucode_expression, AstNode { }

  /** A class representing `expression_statement` nodes. */
  class ExpressionStatement extends @ucode_expression_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ExpressionStatement" }

    /** Gets the child of this node. */
    final AstNode getChild() { ucode_expression_statement_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_expression_statement_def(this, result) }
  }

  /** A class representing `false` tokens. */
  class False extends @ucode_token_false, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "False" }
  }

  /** A class representing `for_alt_statement` nodes. */
  class ForAltStatement extends @ucode_for_alt_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ForAltStatement" }

    /** Gets the node corresponding to the field `body`. */
    final StatementList getBody() { ucode_for_alt_statement_body(this, result) }

    /** Gets the node corresponding to the field `condition`. */
    final AstNode getCondition() { ucode_for_alt_statement_def(this, result, _) }

    /** Gets the node corresponding to the field `increment`. */
    final AstNode getIncrement() { ucode_for_alt_statement_increment(this, result) }

    /** Gets the node corresponding to the field `initializer`. */
    final AstNode getInitializer() { ucode_for_alt_statement_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_for_alt_statement_body(this, result) or
      ucode_for_alt_statement_def(this, result, _) or
      ucode_for_alt_statement_increment(this, result) or
      ucode_for_alt_statement_def(this, _, result)
    }
  }

  /** A class representing `for_in_alt_statement` nodes. */
  class ForInAltStatement extends @ucode_for_in_alt_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ForInAltStatement" }

    /** Gets the node corresponding to the field `body`. */
    final StatementList getBody() { ucode_for_in_alt_statement_body(this, result) }

    /** Gets the node corresponding to the field `key`. */
    final Identifier getKey() { ucode_for_in_alt_statement_key(this, result) }

    /** Gets the node corresponding to the field `kind`. */
    final ReservedWord getKind() { ucode_for_in_alt_statement_kind(this, result) }

    /** Gets the node corresponding to the field `object`. */
    final AstNode getObject() { ucode_for_in_alt_statement_def(this, result) }

    /** Gets the node corresponding to the field `value`. */
    final Identifier getValue() { ucode_for_in_alt_statement_value(this, result) }

    /** Gets the node corresponding to the field `variable`. */
    final Identifier getVariable() { ucode_for_in_alt_statement_variable(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_for_in_alt_statement_body(this, result) or
      ucode_for_in_alt_statement_key(this, result) or
      ucode_for_in_alt_statement_kind(this, result) or
      ucode_for_in_alt_statement_def(this, result) or
      ucode_for_in_alt_statement_value(this, result) or
      ucode_for_in_alt_statement_variable(this, result)
    }
  }

  /** A class representing `for_in_statement` nodes. */
  class ForInStatement extends @ucode_for_in_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ForInStatement" }

    /** Gets the node corresponding to the field `body`. */
    final AstNode getBody() { ucode_for_in_statement_def(this, result, _) }

    /** Gets the node corresponding to the field `key`. */
    final Identifier getKey() { ucode_for_in_statement_key(this, result) }

    /** Gets the node corresponding to the field `kind`. */
    final ReservedWord getKind() { ucode_for_in_statement_kind(this, result) }

    /** Gets the node corresponding to the field `object`. */
    final AstNode getObject() { ucode_for_in_statement_def(this, _, result) }

    /** Gets the node corresponding to the field `value`. */
    final Identifier getValue() { ucode_for_in_statement_value(this, result) }

    /** Gets the node corresponding to the field `variable`. */
    final Identifier getVariable() { ucode_for_in_statement_variable(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_for_in_statement_def(this, result, _) or
      ucode_for_in_statement_key(this, result) or
      ucode_for_in_statement_kind(this, result) or
      ucode_for_in_statement_def(this, _, result) or
      ucode_for_in_statement_value(this, result) or
      ucode_for_in_statement_variable(this, result)
    }
  }

  /** A class representing `for_statement` nodes. */
  class ForStatement extends @ucode_for_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ForStatement" }

    /** Gets the node corresponding to the field `body`. */
    final AstNode getBody() { ucode_for_statement_def(this, result, _, _) }

    /** Gets the node corresponding to the field `condition`. */
    final AstNode getCondition() { ucode_for_statement_def(this, _, result, _) }

    /** Gets the node corresponding to the field `increment`. */
    final AstNode getIncrement() { ucode_for_statement_increment(this, result) }

    /** Gets the node corresponding to the field `initializer`. */
    final AstNode getInitializer() { ucode_for_statement_def(this, _, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_for_statement_def(this, result, _, _) or
      ucode_for_statement_def(this, _, result, _) or
      ucode_for_statement_increment(this, result) or
      ucode_for_statement_def(this, _, _, result)
    }
  }

  /** A class representing `formal_parameters` nodes. */
  class FormalParameters extends @ucode_formal_parameters, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "FormalParameters" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { ucode_formal_parameters_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_formal_parameters_child(this, _, result) }
  }

  /** A class representing `function_declaration` nodes. */
  class FunctionDeclaration extends @ucode_function_declaration, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "FunctionDeclaration" }

    /** Gets the node corresponding to the field `body`. */
    final AstNode getBody() { ucode_function_declaration_body(this, result) }

    /** Gets the node corresponding to the field `name`. */
    final Identifier getName() { ucode_function_declaration_def(this, result, _) }

    /** Gets the node corresponding to the field `parameters`. */
    final FormalParameters getParameters() { ucode_function_declaration_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_function_declaration_body(this, result) or
      ucode_function_declaration_def(this, result, _) or
      ucode_function_declaration_def(this, _, result)
    }
  }

  /** A class representing `function_expression` nodes. */
  class FunctionExpression extends @ucode_function_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "FunctionExpression" }

    /** Gets the node corresponding to the field `body`. */
    final StatementBlock getBody() { ucode_function_expression_def(this, result, _) }

    /** Gets the node corresponding to the field `name`. */
    final Identifier getName() { ucode_function_expression_name(this, result) }

    /** Gets the node corresponding to the field `parameters`. */
    final FormalParameters getParameters() { ucode_function_expression_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_function_expression_def(this, result, _) or
      ucode_function_expression_name(this, result) or
      ucode_function_expression_def(this, _, result)
    }
  }

  /** A class representing `hash_bang_line` tokens. */
  class HashBangLine extends @ucode_token_hash_bang_line, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "HashBangLine" }
  }

  /** A class representing `identifier` tokens. */
  class Identifier extends @ucode_token_identifier, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Identifier" }
  }

  /** A class representing `if_alt_statement` nodes. */
  class IfAltStatement extends @ucode_if_alt_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "IfAltStatement" }

    /** Gets the node corresponding to the field `alternative`. */
    final ElseAltClause getAlternative() { ucode_if_alt_statement_alternative(this, result) }

    /** Gets the node corresponding to the field `condition`. */
    final ParenthesizedExpression getCondition() { ucode_if_alt_statement_def(this, result) }

    /** Gets the node corresponding to the field `consequence`. */
    final StatementList getConsequence() { ucode_if_alt_statement_consequence(this, result) }

    /** Gets the node corresponding to the field `elif_clause`. */
    final ElifClause getElifClause(int i) { ucode_if_alt_statement_elif_clause(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_if_alt_statement_alternative(this, result) or
      ucode_if_alt_statement_def(this, result) or
      ucode_if_alt_statement_consequence(this, result) or
      ucode_if_alt_statement_elif_clause(this, _, result)
    }
  }

  /** A class representing `if_statement` nodes. */
  class IfStatement extends @ucode_if_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "IfStatement" }

    /** Gets the node corresponding to the field `alternative`. */
    final ElseClause getAlternative() { ucode_if_statement_alternative(this, result) }

    /** Gets the node corresponding to the field `condition`. */
    final ParenthesizedExpression getCondition() { ucode_if_statement_def(this, result, _) }

    /** Gets the node corresponding to the field `consequence`. */
    final AstNode getConsequence() { ucode_if_statement_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_if_statement_alternative(this, result) or
      ucode_if_statement_def(this, result, _) or
      ucode_if_statement_def(this, _, result)
    }
  }

  /** A class representing `import_clause` nodes. */
  class ImportClause extends @ucode_import_clause, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ImportClause" }

    /** Gets the node corresponding to the field `default`. */
    final Identifier getDefault() { ucode_import_clause_default(this, result) }

    /** Gets the node corresponding to the field `named`. */
    final NamedImports getNamed() { ucode_import_clause_named(this, result) }

    /** Gets the node corresponding to the field `namespace`. */
    final NamespaceImport getNamespace() { ucode_import_clause_namespace(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_import_clause_default(this, result) or
      ucode_import_clause_named(this, result) or
      ucode_import_clause_namespace(this, result)
    }
  }

  /** A class representing `import_specifier` nodes. */
  class ImportSpecifier extends @ucode_import_specifier, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ImportSpecifier" }

    /** Gets the node corresponding to the field `alias`. */
    final Identifier getAlias() { ucode_import_specifier_alias(this, result) }

    /** Gets the node corresponding to the field `name`. */
    final AstNode getName() { ucode_import_specifier_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_import_specifier_alias(this, result) or ucode_import_specifier_def(this, result)
    }
  }

  /** A class representing `import_statement` nodes. */
  class ImportStatement extends @ucode_import_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ImportStatement" }

    /** Gets the node corresponding to the field `clause`. */
    final ImportClause getClause() { ucode_import_statement_clause(this, result) }

    /** Gets the node corresponding to the field `source`. */
    final String getSource() { ucode_import_statement_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_import_statement_clause(this, result) or ucode_import_statement_def(this, result)
    }
  }

  /** A class representing `lexical_declaration` nodes. */
  class LexicalDeclaration extends @ucode_lexical_declaration, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "LexicalDeclaration" }

    /** Gets the node corresponding to the field `kind`. */
    final AstNode getKind() { ucode_lexical_declaration_kind(this, result) }

    /** Gets the `i`th child of this node. */
    final VariableDeclarator getChild(int i) { ucode_lexical_declaration_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_lexical_declaration_kind(this, result) or
      ucode_lexical_declaration_child(this, _, result)
    }
  }

  /** A class representing `member_expression` nodes. */
  class MemberExpression extends @ucode_member_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "MemberExpression" }

    /** Gets the node corresponding to the field `object`. */
    final Expression getObject() { ucode_member_expression_def(this, result, _) }

    /** Gets the node corresponding to the field `optional_chain`. */
    final OptionalChain getOptionalChain() { ucode_member_expression_optional_chain(this, result) }

    /** Gets the node corresponding to the field `property`. */
    final PropertyIdentifier getProperty() { ucode_member_expression_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_member_expression_def(this, result, _) or
      ucode_member_expression_optional_chain(this, result) or
      ucode_member_expression_def(this, _, result)
    }
  }

  /** A class representing `named_imports` nodes. */
  class NamedImports extends @ucode_named_imports, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "NamedImports" }

    /** Gets the `i`th child of this node. */
    final ImportSpecifier getChild(int i) { ucode_named_imports_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_named_imports_child(this, _, result) }
  }

  /** A class representing `namespace_import` nodes. */
  class NamespaceImport extends @ucode_namespace_import, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "NamespaceImport" }

    /** Gets the child of this node. */
    final Identifier getChild() { ucode_namespace_import_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_namespace_import_def(this, result) }
  }

  /** A class representing `null` tokens. */
  class Null extends @ucode_token_null, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Null" }
  }

  /** A class representing `number` tokens. */
  class Number extends @ucode_token_number, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Number" }
  }

  /** A class representing `object` nodes. */
  class Object extends @ucode_object, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Object" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { ucode_object_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_object_child(this, _, result) }
  }

  /** A class representing `optional_chain` tokens. */
  class OptionalChain extends @ucode_token_optional_chain, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "OptionalChain" }
  }

  /** A class representing `pair` nodes. */
  class Pair extends @ucode_pair, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Pair" }

    /** Gets the node corresponding to the field `key`. */
    final AstNode getKey() { ucode_pair_def(this, result, _) }

    /** Gets the node corresponding to the field `value`. */
    final Expression getValue() { ucode_pair_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_pair_def(this, result, _) or ucode_pair_def(this, _, result)
    }
  }

  /** A class representing `parenthesized_expression` nodes. */
  class ParenthesizedExpression extends @ucode_parenthesized_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ParenthesizedExpression" }

    /** Gets the child of this node. */
    final AstNode getChild() { ucode_parenthesized_expression_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_parenthesized_expression_def(this, result) }
  }

  class PrimaryExpression extends @ucode_primary_expression, AstNode { }

  /** A class representing `program` nodes. */
  class Program extends @ucode_program, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Program" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { ucode_program_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_program_child(this, _, result) }
  }

  /** A class representing `property_identifier` tokens. */
  class PropertyIdentifier extends @ucode_token_property_identifier, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "PropertyIdentifier" }
  }

  /** A class representing `regex` nodes. */
  class Regex extends @ucode_regex, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "Regex" }

    /** Gets the node corresponding to the field `flags`. */
    final RegexFlags getFlags() { ucode_regex_flags(this, result) }

    /** Gets the node corresponding to the field `pattern`. */
    final RegexPattern getPattern() { ucode_regex_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_regex_flags(this, result) or ucode_regex_def(this, result)
    }
  }

  /** A class representing `regex_flags` tokens. */
  class RegexFlags extends @ucode_token_regex_flags, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "RegexFlags" }
  }

  /** A class representing `regex_pattern` tokens. */
  class RegexPattern extends @ucode_token_regex_pattern, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "RegexPattern" }
  }

  /** A class representing `rest_element` nodes. */
  class RestElement extends @ucode_rest_element, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "RestElement" }

    /** Gets the child of this node. */
    final Identifier getChild() { ucode_rest_element_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_rest_element_def(this, result) }
  }

  /** A class representing `return_statement` nodes. */
  class ReturnStatement extends @ucode_return_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ReturnStatement" }

    /** Gets the child of this node. */
    final AstNode getChild() { ucode_return_statement_child(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_return_statement_child(this, result) }
  }

  /** A class representing `sequence_expression` nodes. */
  class SequenceExpression extends @ucode_sequence_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SequenceExpression" }

    /** Gets the `i`th child of this node. */
    final Expression getChild(int i) { ucode_sequence_expression_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_sequence_expression_child(this, _, result) }
  }

  /** A class representing `shorthand_property_identifier` tokens. */
  class ShorthandPropertyIdentifier extends @ucode_token_shorthand_property_identifier, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "ShorthandPropertyIdentifier" }
  }

  /** A class representing `spread_element` nodes. */
  class SpreadElement extends @ucode_spread_element, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SpreadElement" }

    /** Gets the child of this node. */
    final Expression getChild() { ucode_spread_element_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_spread_element_def(this, result) }
  }

  class Statement extends @ucode_statement, AstNode { }

  /** A class representing `statement_block` nodes. */
  class StatementBlock extends @ucode_statement_block, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "StatementBlock" }

    /** Gets the `i`th child of this node. */
    final Statement getChild(int i) { ucode_statement_block_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_statement_block_child(this, _, result) }
  }

  /** A class representing `statement_list` nodes. */
  class StatementList extends @ucode_statement_list, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "StatementList" }

    /** Gets the `i`th child of this node. */
    final Statement getChild(int i) { ucode_statement_list_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_statement_list_child(this, _, result) }
  }

  /** A class representing `string` nodes. */
  class String extends @ucode_string__, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "String" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { ucode_string_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_string_child(this, _, result) }
  }

  /** A class representing `string_fragment` tokens. */
  class StringFragment extends @ucode_token_string_fragment, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "StringFragment" }
  }

  /** A class representing `subscript_expression` nodes. */
  class SubscriptExpression extends @ucode_subscript_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SubscriptExpression" }

    /** Gets the node corresponding to the field `index`. */
    final AstNode getIndex() { ucode_subscript_expression_def(this, result, _) }

    /** Gets the node corresponding to the field `object`. */
    final Expression getObject() { ucode_subscript_expression_def(this, _, result) }

    /** Gets the node corresponding to the field `optional_chain`. */
    final OptionalChain getOptionalChain() {
      ucode_subscript_expression_optional_chain(this, result)
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_subscript_expression_def(this, result, _) or
      ucode_subscript_expression_def(this, _, result) or
      ucode_subscript_expression_optional_chain(this, result)
    }
  }

  /** A class representing `switch_body` nodes. */
  class SwitchBody extends @ucode_switch_body, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SwitchBody" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { ucode_switch_body_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_switch_body_child(this, _, result) }
  }

  /** A class representing `switch_case` nodes. */
  class SwitchCase extends @ucode_switch_case, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SwitchCase" }

    /** Gets the node corresponding to the field `body`. */
    final Statement getBody(int i) { ucode_switch_case_body(this, i, result) }

    /** Gets the node corresponding to the field `value`. */
    final AstNode getValue() { ucode_switch_case_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_switch_case_body(this, _, result) or ucode_switch_case_def(this, result)
    }
  }

  /** A class representing `switch_default` nodes. */
  class SwitchDefault extends @ucode_switch_default, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SwitchDefault" }

    /** Gets the node corresponding to the field `body`. */
    final Statement getBody(int i) { ucode_switch_default_body(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_switch_default_body(this, _, result) }
  }

  /** A class representing `switch_statement` nodes. */
  class SwitchStatement extends @ucode_switch_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "SwitchStatement" }

    /** Gets the node corresponding to the field `body`. */
    final SwitchBody getBody() { ucode_switch_statement_def(this, result, _) }

    /** Gets the node corresponding to the field `value`. */
    final ParenthesizedExpression getValue() { ucode_switch_statement_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_switch_statement_def(this, result, _) or ucode_switch_statement_def(this, _, result)
    }
  }

  /** A class representing `template_string` nodes. */
  class TemplateString extends @ucode_template_string, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "TemplateString" }

    /** Gets the `i`th child of this node. */
    final AstNode getChild(int i) { ucode_template_string_child(this, i, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_template_string_child(this, _, result) }
  }

  /** A class representing `template_substitution` nodes. */
  class TemplateSubstitution extends @ucode_template_substitution, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "TemplateSubstitution" }

    /** Gets the child of this node. */
    final AstNode getChild() { ucode_template_substitution_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_template_substitution_def(this, result) }
  }

  /** A class representing `ternary_expression` nodes. */
  class TernaryExpression extends @ucode_ternary_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "TernaryExpression" }

    /** Gets the node corresponding to the field `alternative`. */
    final Expression getAlternative() { ucode_ternary_expression_def(this, result, _, _) }

    /** Gets the node corresponding to the field `condition`. */
    final Expression getCondition() { ucode_ternary_expression_def(this, _, result, _) }

    /** Gets the node corresponding to the field `consequence`. */
    final Expression getConsequence() { ucode_ternary_expression_def(this, _, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_ternary_expression_def(this, result, _, _) or
      ucode_ternary_expression_def(this, _, result, _) or
      ucode_ternary_expression_def(this, _, _, result)
    }
  }

  /** A class representing `this` tokens. */
  class This extends @ucode_token_this, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "This" }
  }

  /** A class representing `true` tokens. */
  class True extends @ucode_token_true, Token {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "True" }
  }

  /** A class representing `try_statement` nodes. */
  class TryStatement extends @ucode_try_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "TryStatement" }

    /** Gets the node corresponding to the field `body`. */
    final StatementBlock getBody() { ucode_try_statement_def(this, result, _) }

    /** Gets the node corresponding to the field `handler`. */
    final CatchClause getHandler() { ucode_try_statement_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_try_statement_def(this, result, _) or ucode_try_statement_def(this, _, result)
    }
  }

  /** A class representing `unary_expression` nodes. */
  class UnaryExpression extends @ucode_unary_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "UnaryExpression" }

    /** Gets the node corresponding to the field `argument`. */
    final Expression getArgument() { ucode_unary_expression_def(this, result, _) }

    /** Gets the node corresponding to the field `operator`. */
    final string getOperator() {
      exists(int value | ucode_unary_expression_def(this, _, value) |
        result = "!" and value = 0
        or
        result = "+" and value = 1
        or
        result = "-" and value = 2
        or
        result = "~" and value = 3
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_unary_expression_def(this, result, _) }
  }

  /** A class representing `update_expression` nodes. */
  class UpdateExpression extends @ucode_update_expression, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "UpdateExpression" }

    /** Gets the node corresponding to the field `argument`. */
    final AstNode getArgument() { ucode_update_expression_def(this, result, _) }

    /** Gets the node corresponding to the field `operator`. */
    final string getOperator() {
      exists(int value | ucode_update_expression_def(this, _, value) |
        result = "++" and value = 0
        or
        result = "--" and value = 1
      )
    }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() { ucode_update_expression_def(this, result, _) }
  }

  /** A class representing `variable_declarator` nodes. */
  class VariableDeclarator extends @ucode_variable_declarator, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "VariableDeclarator" }

    /** Gets the node corresponding to the field `name`. */
    final Identifier getName() { ucode_variable_declarator_def(this, result) }

    /** Gets the node corresponding to the field `value`. */
    final Expression getValue() { ucode_variable_declarator_value(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_variable_declarator_def(this, result) or ucode_variable_declarator_value(this, result)
    }
  }

  /** A class representing `while_alt_statement` nodes. */
  class WhileAltStatement extends @ucode_while_alt_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "WhileAltStatement" }

    /** Gets the node corresponding to the field `body`. */
    final StatementList getBody() { ucode_while_alt_statement_body(this, result) }

    /** Gets the node corresponding to the field `condition`. */
    final ParenthesizedExpression getCondition() { ucode_while_alt_statement_def(this, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_while_alt_statement_body(this, result) or ucode_while_alt_statement_def(this, result)
    }
  }

  /** A class representing `while_statement` nodes. */
  class WhileStatement extends @ucode_while_statement, AstNode {
    /** Gets the name of the primary QL class for this element. */
    final override string getAPrimaryQlClass() { result = "WhileStatement" }

    /** Gets the node corresponding to the field `body`. */
    final AstNode getBody() { ucode_while_statement_def(this, result, _) }

    /** Gets the node corresponding to the field `condition`. */
    final ParenthesizedExpression getCondition() { ucode_while_statement_def(this, _, result) }

    /** Gets a field or child node of this node. */
    final override AstNode getAFieldOrChild() {
      ucode_while_statement_def(this, result, _) or ucode_while_statement_def(this, _, result)
    }
  }
}
