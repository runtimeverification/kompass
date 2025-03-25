```k
module ACCOUNTS
  imports BOOL
  imports BYTES
  imports INT
  imports STRING

  syntax AccountAddress ::= String // Base58 encoded string

  syntax AccountData ::= "implementme" // Executable MIR? Bytes?

  configuration
    <accounts>
      <account multiplicity="*" type="Map">
        // # Address
        // The account address, a Base58 encoded public key.
        <address> "" </address>

        // # Lamports
        // The account's balance.
        // 1 SOL = 1 Billion lamports.
        <lamports> 0 </lamports>

        // # Account Data
        // For executable accounts, this holds the executable data.
        // For non-executable accounts, this generally stores state and is read-only.
        <data> implementme </data>

        // # Account Owner
        // The default owner is the System Program.
        // Only the owner is able to modify an account's data or deduct lamports.
        <owner> "11111111111111111111111111111111" </owner>

        // # Executable flag
        <executable> false </executable>

        // # Rent Epoch
        // Legacy field, no longer used.
        <rent-epoch> 0 </rent-epoch>
      </account>
    </accounts>

endmodule
```
