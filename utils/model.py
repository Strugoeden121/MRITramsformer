import torch
import torch.nn as nn
import torch.nn.functional as F

from MRITramsformer.utils.constants import INPUT_NUM_FRAMES, INPUT_NUM_SHOTS, INPUT_NUM_SAMPLES, IN_CHANNELS, OUT_CHANNELS,FEATURE_DIM

class BasicTransformerTraj(nn.Module):
    def __init__(self):
        super(BasicTransformerTraj, self).__init__()
        self.encoder = nn.Conv2d(in_channels=IN_CHANNELS, out_channels=FEATURE_DIM, kernel_size=3, stride=1, padding=1)
        # Adaptive pooling to reduce spatial dimensions to a fixed feature dimension
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))  # Output shape: (batch_size, FEATURE_DIM, 1, 1)
        
        self. transformer = nn.Transformer(d_model=FEATURE_DIM, nhead=4, num_encoder_layers=6)

        self.linear = nn.Linear(FEATURE_DIM, INPUT_NUM_SHOTS * INPUT_NUM_SAMPLES)

    def forward(self, x, batch_size):
        #reshaped_x = x.view(INPUT_NUM_FRAMES, 1, INPUT_NUM_SHOTS, INPUT_NUM_SAMPLES)
        encode_out = self.encoder(x)
        pooled_out = self.global_pool(encode_out)  # Shape: (batch_size, FEATURE_DIM, 1, 1)

        # Step 3: Reshape to (batch_size, 1, FEATURE_DIM)
        reshaped_encode_out = pooled_out.view(batch_size, 1, FEATURE_DIM)  
       # reshaped_encode_out = encode_out.permute(2, 0, 3,
                                 #                1).contiguous()  # Shape: [INPUT_NUM_SHOTS, batch_size, INPUT_NUM_SAMPLES, OUT_CHANNELS]
        #reshaped_encode_out = reshaped_encode_out.view(batch_size,
                           #                            -1)  # Merge last two dims for d_model
        #reshaped_encode_out = reshaped_encode_out.unsqueeze(1)  # Add seq dim
        
        predictions = torch.zeros(batch_size, INPUT_NUM_FRAMES, FEATURE_DIM)
        # Autoregressive loop over frames
        current_input = reshaped_encode_out[:, :, :]  # Start with the first input

        for t in range(INPUT_NUM_FRAMES-1):
            
            output = self.transformer(current_input.permute(1, 0, 2), reshaped_encode_out.permute(1, 0, 2))
            output = output.permute(1,0,2)
            predictions[:, t, :] = reshaped_encode_out[:, 0, :]
           

            current_input = torch.cat((current_input[:, :, :], output[:, 0, :].unsqueeze(1)), dim=1)

            # Update current_input for next time step
            #current_input = output[:, 0, :, :].unsqueeze(1)
            
            
        current_input = self.linear(current_input)

        current_input = current_input.reshape(batch_size, INPUT_NUM_FRAMES, INPUT_NUM_SHOTS, INPUT_NUM_SAMPLES)
        return current_input


class BasicTransformerShot(nn.Module):
    def __init__(self):
        super(BasicTransformerShot, self).__init__()
        self.encoder = nn.Conv2d(in_channels=IN_CHANNELS, out_channels=OUT_CHANNELS, kernel_size=3, stride=1, padding=1)
        self.transformer = nn.Transformer(d_model=INPUT_NUM_SAMPLES, nhead=3, num_encoder_layers=6)

    def forward(self, x, only_last_frame=False, time_stamp=None):
        batch_size, channels, shots, samples = x.size()
        if time_stamp is not None:
            out_batch_size = batch_size // time_stamp
            output = torch.zeros(out_batch_size, INPUT_NUM_SHOTS, samples)
        # reshaped_x = x.view(INPUT_NUM_FRAMES, 1, INPUT_NUM_SHOTS, INPUT_NUM_SAMPLES)
        encode_out = self.encoder(x)
        reshaped_encode_out = encode_out.permute(2, 0, 3,
                                                 1).contiguous()  # Shape: [INPUT_NUM_SHOTS, batch_size, INPUT_NUM_SAMPLES, OUT_CHANNELS]
        reshaped_encode_out = reshaped_encode_out.view(INPUT_NUM_SHOTS, batch_size,
                                                       -1)  # Merge last two dims for d_model
        if only_last_frame:
            output = self.transformer(reshaped_encode_out, reshaped_encode_out)
        else:
            output = self.transformer(reshaped_encode_out.permute(1, 0, 2), output)
        output = output.reshape(INPUT_NUM_SHOTS, out_batch_size, OUT_CHANNELS, INPUT_NUM_SAMPLES).permute(1, 2, 0,
                                                                                                   3).contiguous()
        return output
    
    
if __name__ == '__main__':
    model = BasicTransformerTraj()
    x = torch.randn(INPUT_NUM_FRAMES, INPUT_NUM_SHOTS, INPUT_NUM_SAMPLES)
    y = model(x)
    print(y.shape)
    