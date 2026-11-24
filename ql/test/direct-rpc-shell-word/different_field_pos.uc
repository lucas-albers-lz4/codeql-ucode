import { popen } from 'fs';
const methods = {
  otherMethod: {
    call: function(input) {
      return popen(`printf %s ${input.args.other_field} end`);
    }
  }
};
return { other: methods };
