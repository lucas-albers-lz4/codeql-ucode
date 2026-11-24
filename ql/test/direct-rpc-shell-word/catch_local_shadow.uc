import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      let command;
      command = `echo ${input.args.value} done`;
      try { throw 'echo constant done'; }
      catch (command) { return popen(command); }
    }
  }
};
return { probe: methods };
