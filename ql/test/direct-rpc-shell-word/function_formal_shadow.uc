import { popen } from 'fs';
const methods = {
  probe: {
    call: function(input) {
      function input() { return { args: { value: 'constant' } }; }
      return popen(`echo ${input.args.value} done`);
    }
  }
};
return { probe: methods };
