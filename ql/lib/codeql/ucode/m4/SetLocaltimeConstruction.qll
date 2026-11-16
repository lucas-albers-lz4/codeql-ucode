import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.Diagnostics

/** This is a source-shape subset, not builtin target resolution. */
predicate plainUnique(UCODE::Object obj) {
  not exists(UCODE::AstNode child |
    child = obj.getChild(_) and
    not exists(UCODE::Pair pair | pair = child and exists(pair.getKey().(UCODE::PropertyIdentifier)))
  ) and
  not exists(UCODE::Pair a, UCODE::Pair b |
    a = obj.getChild(_) and b = obj.getChild(_) and a != b and
    a.getKey().(UCODE::PropertyIdentifier).getValue() = b.getKey().(UCODE::PropertyIdentifier).getValue()
  )
}

predicate validEntry(UCODE::AstNode node) {
  exists(UCODE::Pair pair, UCODE::Object body, UCODE::Pair call |
    pair = node and exists(pair.getKey().(UCODE::PropertyIdentifier)) and
    body = pair.getValue() and plainUnique(body) and
    call = body.getChild(_) and call.getKey().(UCODE::PropertyIdentifier).getValue() = "call" and
    exists(call.getValue().(UCODE::FunctionExpression))
  )
}

predicate plainString(UCODE::String s, string value) {
  s.getChild(0).(UCODE::StringFragment).getValue() = value and
  not exists(s.getChild(1))
}

predicate directCall(UCODE::CallExpression c, string name, int arity) {
  c.getFunction().(UCODE::Identifier).getValue() = name and
  not exists(c.getOptionalChain()) and
  (arity = 1 and exists(c.getArguments().getChild(0)) and not exists(c.getArguments().getChild(1)) or
   arity = 7 and exists(c.getArguments().getChild(6)) and not exists(c.getArguments().getChild(7)))
}

predicate allowedCalleeName(UCODE::Program p, string name) {
  name = ["system", "sprintf", "localtime"] and
  not exists(UCODE::Identifier id |
    id.getLocation().getFile() = p.getLocation().getFile() and id.getValue() = name and
    not exists(UCODE::CallExpression call |
      call.getFunction() = id and not exists(call.getOptionalChain())
    )
  ) and
  not exists(UCODE::ShorthandPropertyIdentifier id |
    id.getLocation().getFile() = p.getLocation().getFile() and id.getValue() = name
  )
}

predicate inputExpr(UCODE::MemberExpression access) {
  access.getProperty().getValue() = "localtime" and not exists(access.getOptionalChain()) and
  exists(UCODE::MemberExpression args |
    access.getObject() = args and not exists(args.getOptionalChain()) and
    args.getProperty().getValue() = "args" and args.getObject().(UCODE::Identifier).getValue() = "request"
  )
}

predicate slot(int i, string name, string conversion) {
  i = 1 and name = "year" and conversion = "%04d" or
  i = 2 and name = "mon" and conversion = "%02d" or
  i = 3 and name = "mday" and conversion = "%02d" or
  i = 4 and name = "hour" and conversion = "%02d" or
  i = 5 and name = "min" and conversion = "%02d" or
  i = 6 and name = "sec" and conversion = "%02d"
}

pragma[noinline]
predicate ownedCallback(UCODE::Program p, UCODE::FunctionExpression fn) {
  not exists(ExtractionError error | error.getLocation().getFile() = p.getLocation().getFile()) and
  exists(UCODE::LexicalDeclaration dec, UCODE::VariableDeclarator binding, UCODE::Object methods,
    UCODE::ReturnStatement ret, UCODE::Object returned, UCODE::Pair rp, UCODE::Pair entry,
    UCODE::Object method, UCODE::Pair call, UCODE::Pair args, UCODE::Object argobj, UCODE::Pair arg |
    dec = p.getChild(_) and dec.getKind().(UCODE::Token).getValue() = "const" and
    binding = dec.getChild(_) and binding.getName().getValue() = "methods" and methods = binding.getValue() and
    ret = p.getChild(_) and returned = ret.getChild() and plainUnique(returned) and
    not exists(UCODE::ReturnStatement other | other = p.getChild(_) and other != ret) and
    rp = returned.getChild(_) and rp.getKey().(UCODE::PropertyIdentifier).getValue() = "luci" and
    rp.getValue().(UCODE::Identifier).getValue() = "methods" and
    not exists(UCODE::Identifier id |
      id.getLocation().getFile() = p.getLocation().getFile() and id.getValue() = "methods" and
      id != binding.getName() and id != rp.getValue()
    ) and
    not exists(UCODE::ShorthandPropertyIdentifier id |
      id.getLocation().getFile() = p.getLocation().getFile() and id.getValue() = "methods"
    ) and
    plainUnique(methods) and not exists(UCODE::AstNode child | child = methods.getChild(_) and not validEntry(child)) and
    entry = methods.getChild(_) and entry.getKey().(UCODE::PropertyIdentifier).getValue() = "setLocaltime" and
    method = entry.getValue() and plainUnique(method) and
    call = method.getChild(_) and call.getKey().(UCODE::PropertyIdentifier).getValue() = "call" and fn = call.getValue() and
    args = method.getChild(_) and args.getKey().(UCODE::PropertyIdentifier).getValue() = "args" and
    argobj = args.getValue() and arg = argobj.getChild(0) and not exists(argobj.getChild(1)) and
    arg.getKey().(UCODE::PropertyIdentifier).getValue() = "localtime" and arg.getValue().(UCODE::Number).getValue() = "0"
  ) and
  allowedCalleeName(p, "system") and allowedCalleeName(p, "sprintf") and allowedCalleeName(p, "localtime")
}

pragma[noinline]
predicate construction(UCODE::Program p, UCODE::FunctionExpression fn,
    UCODE::CallExpression initializer, UCODE::MemberExpression input, UCODE::Identifier guard,
    UCODE::CallExpression formatter, UCODE::String format, UCODE::CallExpression sink) {
  ownedCallback(p, fn) and
  not exists(fn.getName()) and fn.getParameters().getChild(0).(UCODE::Identifier).getValue() = "request" and
  not exists(fn.getParameters().getChild(1)) and
  exists(UCODE::StatementBlock body, UCODE::LexicalDeclaration dec, UCODE::VariableDeclarator v,
    UCODE::IfStatement cond, UCODE::StatementBlock thenBlock, UCODE::ReturnStatement ret,
    UCODE::Object retobj, UCODE::Pair resultPair, UCODE::MemberExpression input2,
    UCODE::ExpressionStatement sinkstmt, UCODE::ExpressionStatement siblingstmt, UCODE::CallExpression sibling,
    UCODE::String siblingarg |
    body = fn.getBody() and dec = body.getChild(0) and cond = body.getChild(1) and ret = body.getChild(2) and
    not exists(body.getChild(3)) and dec.getKind().(UCODE::Token).getValue() = "let" and
    v = dec.getChild(0) and not exists(dec.getChild(1)) and v.getName().getValue() = "t" and
    initializer = v.getValue() and directCall(initializer, "localtime", 1) and
    input = initializer.getArguments().getChild(0) and inputExpr(input) and
    guard = cond.getCondition().getChild() and guard.getValue() = "t" and not exists(cond.getAlternative()) and
    thenBlock = cond.getConsequence() and sinkstmt = thenBlock.getChild(0) and siblingstmt = thenBlock.getChild(1) and
    not exists(thenBlock.getChild(2)) and sink = sinkstmt.getChild() and directCall(sink, "system", 1) and
    formatter = sink.getArguments().getChild(0) and directCall(formatter, "sprintf", 7) and
    format = formatter.getArguments().getChild(0) and
    plainString(format, "date -s \"%04d-%02d-%02d %02d:%02d:%02d\" >/dev/null") and
    sibling = siblingstmt.getChild() and directCall(sibling, "system", 1) and
    siblingarg = sibling.getArguments().getChild(0) and plainString(siblingarg, "/etc/init.d/sysfixtime restart >/dev/null") and
    retobj = ret.getChild() and resultPair = retobj.getChild(0) and not exists(retobj.getChild(1)) and
    resultPair.getKey().(UCODE::PropertyIdentifier).getValue() = "result" and input2 = resultPair.getValue() and inputExpr(input2) and
    not exists(int i, string n, string c |
      slot(i, n, c) and not exists(UCODE::MemberExpression field |
        field = formatter.getArguments().getChild(i) and not exists(field.getOptionalChain()) and
        field.getObject().(UCODE::Identifier).getValue() = "t" and field.getProperty().getValue() = n
      )
    ) and
    not exists(UCODE::Identifier id |
      id.getParent*() = fn and id.getValue() = "t" and id != v.getName() and id != guard and
      not exists(UCODE::MemberExpression field, int i, string n, string c |
        slot(i, n, c) and field = formatter.getArguments().getChild(i) and field.getObject() = id
      )
    ) and
    not exists(UCODE::Identifier id |
      id.getParent*() = fn and id.getValue() = "request" and id != fn.getParameters().getChild(0) and
      id != input.getObject().(UCODE::MemberExpression).getObject() and
      id != input2.getObject().(UCODE::MemberExpression).getObject()
    ) and
    not exists(UCODE::ShorthandPropertyIdentifier id |
      id.getParent*() = fn and id.getValue() = ["t", "request"]
    )
  )
}
