```k
module ACCOUNTS
  imports INT
  imports BOOL
  imports BYTES

  configuration
    <account>
      <lamports> 0 </lamports>
      <data> .Bytes </data>
      <owner> 0 </owner>
      <executable> false </executable>
      <rent-epoch> 0 </rent-epoch>
    </account>

endmodule
```
