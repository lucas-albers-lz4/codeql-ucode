function shadowed(system, request) {
  system(request.args.command);
}
function builtin(request) {
  system(request.args.command);
}
function outer(request) {
  function system(command) { return command; }
  system(request.args.command);
}
function lexical(request) {
  {
    let system = function(command) { return command; };
    system(request.args.command);
  }
  system(request.args.command);
}
function before_declaration(request) {
  system(request.args.command);
  let system = function(command) { return command; };
}
function more(request) {
  let f = function(...system) { system(request.args.command); };
  let g = function system(command) { system(request.args.command); };
  for (let system in []) { system(request.args.command); }
  try { fail(); } catch (system) { system(request.args.command); }
  let h = system => system(request.args.command);
  {
    const system = function(command) { return command; };
    function closure() { system(request.args.command); }
  }
  system(request.args.command);
  for (let system in system(request.args.command)) { }
}
function switch_variable(request) {
  switch (1) {
    case 1:
      let system = function(command) { return command; };
      system(request.args.command); // shadowed inside switch
    case 2:
      system(request.args.command); // shared across cases
      break;
  }
  system(request.args.command); // builtin after switch
}
function switch_function(request) {
  switch (1) {
    case 1:
      function system(command) { return command; }
      system(request.args.command); // shadowed inside switch
      break;
  }
  system(request.args.command); // builtin after switch
}
function counting_loop(request) {
  for (let i = 0; i < 1; i++)
    function system(command) { system(request.args.command); } // shadowed inside loop
  system(request.args.command); // builtin after counting loop
}
function iteration_loop(request) {
  for (let item in [1])
    function system(command) { system(request.args.command); } // shadowed inside loop
  system(request.args.command); // builtin after for-in loop
}
function while_control(request) {
  while (false)
    function system(command) { return command; }
  system(request.args.command); // while does not create a scope
}

// A binding in one function must not suppress the builtin in its sibling.
function sibling_let_shadow(request) {
  let system = function(command) { return command; };
  system(request.args.command); // sibling shadow: let
}
function sibling_let_builtin(request) {
  system(request.args.command); // sibling builtin: let
}
function sibling_function_shadow(request) {
  function system(command) { return command; }
  system(request.args.command); // sibling shadow: function
}
function sibling_function_builtin(request) {
  system(request.args.command); // sibling builtin: function
}
function sibling_parameter_shadow(system, request) {
  system(request.args.command); // sibling shadow: parameter
}
function sibling_parameter_builtin(request) {
  system(request.args.command); // sibling builtin: parameter
}
function sibling_rest_shadow(request, ...system) {
  system(request.args.command); // sibling shadow: rest
}
function sibling_rest_builtin(request) {
  system(request.args.command); // sibling builtin: rest
}
function sibling_catch_shadow(request) {
  try { fail(); } catch (system) {
    system(request.args.command); // sibling shadow: catch
  }
}
function sibling_catch_builtin(request) {
  system(request.args.command); // sibling builtin: catch
}
