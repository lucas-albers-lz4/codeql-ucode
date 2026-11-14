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
