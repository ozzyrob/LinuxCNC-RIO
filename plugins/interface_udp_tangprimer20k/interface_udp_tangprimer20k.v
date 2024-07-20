

module interface_udp_tangprimer20k
    #(parameter BUFFER_SIZE=80, parameter MSGID=32'h74697277, parameter MAC={8'h06,8'h00,8'hAA,8'hBB,8'h0C,8'hDD}, parameter IP={8'd192,8'd168,8'd10,8'd14}, parameter TIMEOUT=32'd4800000)
     (
         input sysclk,
         input clk1m,
         output reg [BUFFER_SIZE-1:0] rx_data,
         input [BUFFER_SIZE-1:0] tx_data,
         output pkg_timeout,
         output phyrst,
         input netrmii_clk50m,
         input netrmii_rx_crs,
         output netrmii_mdc,
         output netrmii_txen,
         inout netrmii_mdio,
         output netrmii_txd_0,
         output netrmii_txd_1,
         input netrmii_rxd_0,
         input netrmii_rxd_1
     );

    reg [31:0] timeout_counter = 0;
    reg timeout = 1;
    assign pkg_timeout = timeout;

    reg soft_rst = 0;
    reg [31:0] rst_counter = 0;
    always @(posedge sysclk) begin
        if (rst_counter < 27000000) begin
            rst_counter <= rst_counter + 1;
        end else begin
            soft_rst <= 1;
        end
    end

    reg [BUFFER_SIZE-1:0] tx_data_buffer;
    reg [BUFFER_SIZE-1:0] rx_data_buffer;

    wire clk50m;
    wire ready;
    wire eth_rx_head_av;
    wire [31:0] eth_rx_head;
    wire eth_rx_data_av;
    wire [7:0] eth_rx_data;
    reg eth_rx_head_rdy;
    reg [31:0] eth_tx_ip;
    reg [15:0] eth_tx_dst_port;
    reg eth_tx_req;
    reg [7:0] eth_tx_data;
    reg eth_tx_data_av;
    wire eth_tx_req_rdy;
    wire eth_tx_data_rdy;

    udp #(
            .ip_adr(IP),
            .mac_adr(MAC),

            .arp_refresh_interval(50000000*30), // 30 seconds
            .arp_max_life_time(50000000*50) // 50 seconds
        )udp_inst(
            .clk1m(clk1m),
            .rst(soft_rst),
            .clk50m(clk50m),
            .ready(ready),
            .netrmii_clk50m(netrmii_clk50m),
            .netrmii_rx_crs(netrmii_rx_crs),
            .netrmii_mdc(netrmii_mdc),
            .netrmii_txen(netrmii_txen),
            .netrmii_mdio(netrmii_mdio),
            .netrmii_txd({netrmii_txd_1, netrmii_txd_0}),
            .netrmii_rxd({netrmii_rxd_1, netrmii_rxd_0}),
            .phyrst(phyrst),

            .rx_head_rdy_i(eth_rx_head_rdy),
            .rx_head_av_o(eth_rx_head_av),
            .rx_head_o(eth_rx_head),
            .rx_data_rdy_i(1'b1),
            .rx_data_av_o(eth_rx_data_av),
            .rx_data_o(eth_rx_data),

            .tx_ip_i(eth_tx_ip),
            .tx_src_port_i(16'd2390),
            .tx_dst_port_i(eth_tx_dst_port),
            .tx_req_i(eth_tx_req),
            .tx_data_i(eth_tx_data),
            .tx_data_av_i(eth_tx_data_av),
            .tx_req_rdy_o(eth_tx_req_rdy),
            .tx_data_rdy_o(eth_tx_data_rdy)
        );

    reg [3:0] eth_rx_state = 4'd0;
    reg [3:0] eth_tx_state = 4'd0;
    reg [7:0] eth_rx_counter = 8'd0;
    reg [7:0] eth_tx_counter = 8'd0;

    always @(posedge clk50m or negedge ready) begin
        if (ready == 0) begin
            eth_tx_state <= 4'd0;
            eth_rx_state <= 4'd0;
            eth_rx_counter <= 8'd0;
            eth_tx_counter <= 8'd0;
            eth_tx_req <= 0;
        end else begin

            // check timeout
            if (timeout_counter < TIMEOUT) begin
                timeout_counter <= timeout_counter + 1;
                timeout <= 0;
            end else begin
                //timeout <= 1;
            end

            // rx data
            if (eth_rx_data_av) begin
                // receive data
                rx_data_buffer <= {rx_data_buffer[BUFFER_SIZE-1-8:0], eth_rx_data};
                eth_rx_counter <= eth_rx_counter + 8'd1;
            end else begin
                // wait for end of rx
                if (eth_rx_state == 4'd4) begin
                    // check and save rx data
                    if (eth_rx_counter >= BUFFER_SIZE/8 && rx_data_buffer[BUFFER_SIZE-1:BUFFER_SIZE-32] == MSGID) begin
                        rx_data <= rx_data_buffer;
                        timeout_counter <= 0;
                        // trigger next tx
                        eth_tx_state <= 4'd1;
                    end
                    // ready for next rx
                    eth_rx_state <= 4'd0;
                    eth_rx_counter <= 8'd0;
                end
            end

            // receive
            case(eth_rx_state)
                0:begin
                    // wait for header
                    if (eth_rx_head_av) begin
                        eth_rx_head_rdy <= 1'b1;
                        eth_rx_state <= 4'd1;
                    end else begin
                        eth_rx_head_rdy <= 1'b0;
                    end
                end
                1:begin
                    // read ip from header
                    eth_tx_ip <= eth_rx_head;
                    eth_rx_state <= 4'd2;
                end
                2:begin
                    // read ??? from header
                    eth_rx_state <= 4'd3;
                end
                3:begin
                    // read port from header
                    if (eth_rx_head[15:0] == 16'd2390) begin
                        eth_tx_dst_port <= eth_rx_head[31:16];
                        eth_rx_state <= 4'd4;
                    end else begin
                        eth_rx_state <= 4'd0;
                    end
                end
                4:begin
                    // wait for data received
                end
            endcase


            // transmit
            case(eth_tx_state)
                0:begin
                    // wait for trigger by new rx package
                end
                1:begin
                    // wait for tx ready
                    if (eth_tx_req_rdy) begin
                        // set data to transmit
                        eth_tx_counter <= 8'd0;
                        tx_data_buffer <= tx_data;
                        eth_tx_state <= 4'd2;
                    end
                end
                2:begin
                    // send data
                    if (eth_tx_counter < BUFFER_SIZE/8) begin
                        eth_tx_data_av <= 1;
                        eth_tx_data <= tx_data_buffer[BUFFER_SIZE-1:BUFFER_SIZE-8];
                        tx_data_buffer <= {tx_data_buffer[BUFFER_SIZE-9:0], 8'd0};
                        eth_tx_counter = eth_tx_counter + 8'd1;
                    end else begin
                        eth_tx_data_av <= 0;
                        eth_tx_state <= 4'd3;
                    end
                end
                3:begin
                    // start transmit
                    if (eth_tx_req_rdy) begin
                        eth_tx_req <= 1'b1;
                        eth_tx_state <= 4'd4;
                    end
                end
                4:begin
                    // transmit done
                    eth_tx_req <= 1'b0;
                    eth_tx_state <= 4'd0;
                end
            endcase
        end
    end

endmodule
