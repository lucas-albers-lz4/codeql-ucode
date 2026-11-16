const methods = {
  setLocaltime: {
    args: { localtime: 0 },
    call: function(request) {
      let t = localtime(request.args.localtime);
      if (t) {
        system(sprintf('date -s "%04d-%02d-%02d %02d:%02d:%02d" >/dev/null', t.year, t.mon, t.mday, t.hour, t.min, t.sec));
        system('/etc/init.d/sysfixtime restart >/dev/null');
      }
      return { result: request.args.localtime };
    }
  }
};
return { luci: methods };
