`timescale 1ns/100ps

module testb;
    reg clk = 0;
    always #2 clk = !clk;

    reg jointEnable = 1;
    reg signed [31:0] jointFreqCmd = 32'd0;
    wire signed [31:0] jointFeedback;

    wire PWM;

    initial begin
        $dumpfile("testb.vcd");
        $dumpvars(0, clk);
        $dumpvars(1, jointFreqCmd);
        $dumpvars(2, jointFeedback);
        $dumpvars(3, PWM);

        # 3000000 jointFreqCmd = 32'd50000;
        # 3000000 $finish;
    end

    joint_pwmdir joint_pwmdir1 (
                     .clk (clk),
                     .jointEnable (jointEnable),
                     .jointFreqCmd (jointFreqCmd),
                     .jointFeedback (jointFeedback),
                     .PWM (PWM)
                 );

endmodule
