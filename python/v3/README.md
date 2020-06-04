# Description

This is an update of the Trajectory Prediction Python code for use with PyWren.

# Updates

- Compute multiple result per object, in different future time points.

- Input samples are NOT equally apart in time.

- It has some global variables to manage some details about the predictions:

  - QUAD_REG_LEN = 20 # max amount of trajectory points to manage
  - QUAD_REG_OFFSET = 5 # how many points to predict
  - QUAD_REG_MIN = 5 # min amount of trajectory points to start predicting
  - PRED_RANGE_MIL = 200 # range for predicted points in milliseconds 

- Now it is working with the new function ```traj_pred_v2()``` proposed to calculate the predicted trajectory with less computation efforts

  - Predict X and Y over T with the quadratic regression function.


## License

Apache 2.0

By downloading this software, the downloader agrees with the specified terms and conditions of the License Agreement and the particularities of the license provided.
