
module vin_pwmcounter
    #(parameter RESET_CNT = 25000000)
     (
         input clk,
         input SIGNAL,
         output [31:0] frequency
     );
    reg [31:0] freq_cnt = 0;
    reg[31:0] freq = 0;
    assign frequency = freq;

    reg[2:0] SIGr;  always @(posedge clk) SIGr <= {SIGr[1:0], SIGNAL};
    wire SIG_risingedge = (SIGr[2:1]==2'b01);
    wire SIG_fallingedge = (SIGr[2:1]==2'b10);

    always @(posedge clk)
    begin
        if (SIG_fallingedge) begin
            freq <= freq_cnt + 1;
        end else if (SIG_risingedge) begin
            freq_cnt <= 0;
        end else begin
            freq_cnt <= freq_cnt + 1;
            if (freq_cnt > RESET_CNT) begin
                freq <= RESET_CNT;
                freq_cnt <= 0;
            end
        end
    end
endmodule
