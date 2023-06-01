
module debouncer
    #(parameter WIDTH = 16)
    (
        input clk,
        input SIGNAL,
        output reg SIGNAL_state
    );

    reg SIGNAL_sync_0;  always @(posedge clk) SIGNAL_sync_0 <= ~SIGNAL;
    reg SIGNAL_sync_1;  always @(posedge clk) SIGNAL_sync_1 <= SIGNAL_sync_0;
    reg [WIDTH-1:0] SIGNAL_cnt;
    wire SIGNAL_idle = (SIGNAL_state == SIGNAL_sync_1);
    wire SIGNAL_cnt_max = &SIGNAL_cnt;

    always @(posedge clk)
    if (SIGNAL_idle) begin
        SIGNAL_cnt <= 0;
    end else begin
        SIGNAL_cnt <= SIGNAL_cnt + 1;
        if (SIGNAL_cnt_max) begin
            SIGNAL_state <= ~SIGNAL_state;
        end
    end
endmodule
