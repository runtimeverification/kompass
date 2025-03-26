```k
requires "accounts.md"

module TRANSACTIONS
  imports ACCOUNTS
  imports LIST
  imports BOOL
  imports BYTES

  syntax Transaction
     ::= transaction(
           message: Message,
           signatures: List, // List<String>
         )

  syntax Message
     ::= message(
           header: MessageHeader,
           accounts: List, // List<AccountAddress>
           recent_blockhash: Int,
           instructions: List // List<Instruction>
         )

  syntax MessageHeader
     ::= message_header(
           num_required_signatures: Int,
           num_readonly_signed_accounts: Int,
           num_readonly_unsigned_accounts: Int
         )

  syntax Instruction
     ::= instruction(
           // Public key of the program to execute this instruction
           program_id: AccountAddress,

           accounts: List, // List<AccountMeta>

           // Passed to the program
           data: Bytes
         )

  syntax AccountMeta
     ::= account_meta(
           pubkey: AccountAddress,

           // True if the instruction requires the transaction signature to match this account
           is_signer: Bool,

           // True if the account data may be mutated during execution
           is_writable: Bool,
         )
endmodule
```
