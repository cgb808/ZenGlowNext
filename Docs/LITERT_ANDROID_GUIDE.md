## LiteRT for Android

LiteRT lets you run TensorFlow, PyTorch, and JAX models in your Android apps. The LiteRT system provides prebuilt and customizable execution environments for running models on Android quickly and efficiently, including options for hardware acceleration.

For example Android applications that use LiteRT, see the LiteRT samples repository.

### Machine learning models

LiteRT uses TensorFlow, PyTorch, and JAX models that are converted into a smaller, portable, more efficient machine learning model format. You can use prebuilt models with LiteRT on Android, or build your own models and convert them to LiteRT format.

This page discusses using already-built machine learning models and does not cover building, training, testing, or converting models. Learn more about picking, modifying, building, and converting machine learning models for LiteRT in the Models page.

### Run models on Android

A LiteRT model running inside an Android app takes in data, processes the data, and generates a prediction based on the model's logic. A LiteRT model requires a special runtime environment in order to execute, and the data that is passed into the model must be in a specific data format, called a tensor. When a model processes the data, known as running an inference, it generates prediction results as new tensors, and passes them to the Android app so it can take action, such as showing the result to a user or executing additional business logic.

**Functional execution flow for LiteRT models in Android apps**

Figure 1. Functional execution flow for LiteRT models in Android apps.

At the functional design level, your Android app needs the following elements to run a LiteRT model:

*   LiteRT runtime environment for executing the model
*   Model input handler to transform data into tensors
*   Model output handler to receive output result tensors and interpret them as prediction results

The following sections describe how the LiteRT libraries and tools provide these functional elements.

### Build apps with LiteRT

This section describes the recommended, most common path for implementing LiteRT in your Android App. You should pay most attention to the runtime environment and development libraries sections. If you have developed a custom model, make sure to review the Advanced development paths section.

#### Runtime environment options

There are several ways you can enable a runtime environment for executing models in your Android app. These are the preferred options:

*   LiteRT in Google Play services runtime environment (recommended)
*   Stand-alone LiteRT runtime environment

In general, you should use the runtime environment provided by Google Play services because it is more space-efficient than the standard environment since it loads dynamically, keeping your app size smaller. Google Play services also automatically uses the most recent, stable release of the LiteRT runtime, giving you additional features and improved performance over time. If you offer your app on devices that do not include Google Play services or you need to closely manage your ML runtime environment, then you should use the standard LiteRT runtime. This option bundles additional code into your app, allowing you to have more control over the ML runtime in your app at the cost of increasing your app's download size.

You access these runtime environments in your Android app by adding LiteRT development libraries to your app development environment. For information about how to use the standard runtime environments in your app, see the next section.

**Note:** Some advanced use cases may require customization of model runtime environment, which are described in the Advanced runtime environments section.

#### Libraries

You can access the Interpreter API using the Google Play services. You can use the LiteRT core and support libraries in your Android app. For programming details about using LiteRT libraries and runtime environments, see Development tools for Android.

#### Obtain models

Running a model in an Android app requires a LiteRT-format model. You can use prebuilt models or build one and convert it to the Lite format. For more information on obtaining models for your Android app, see the LiteRT Models page.

#### Handle input data

Any data you pass into a ML model must be a tensor with a specific data structure, often called the shape of the tensor. To process data with a model, your app code must transform data from its native format, such as image, text, or audio data, into a tensor in the required shape for your model.

**Note:** Many LiteRT models come with embedded metadata that describes the required input data.

#### Run inferences

Processing data through a model to generate a prediction result is known as running an inference. Running an inference in an Android app requires a LiteRT runtime environment, a model and input data.

The speed at which a model can generate an inference on a particular device depends on the size of the data processed, the complexity of the model, and the available computing resources such as memory and CPU, or specialized processors called accelerators. Machine learning models can run faster on these specialized processors such as graphics processing units (GPUs) and tensor processing units (TPUs), using LiteRT hardware drivers called delegates. For more information about delegates and hardware acceleration of model processing, see the Hardware acceleration overview.

#### Handle output results

Models generate prediction results as tensors, which must be handled by your Android app by taking action or displaying a result to the user. Model output results can be as simple as a number corresponding to a single result (0 = dog, 1 = cat, 2 = bird) for an image classification, to much more complex results, such as multiple bounding boxes for several classified objects in an image, with prediction confidence ratings between 0 and 1.

**Note:** Many LiteRT models come with embedded metadata that describes the output results of a model and how to interpret it.

### Advanced development paths

When using more sophisticated and customized LiteRT models, you may need to use more advanced development approaches than what is described above. The following sections describe advanced techniques for executing models and developing them for LiteRT in Android apps.

#### Advanced runtime environments

In addition to the standard runtime and Google Play services runtime environments for LiteRT, there are additional runtime environments you can use with your Android app. The most likely use for these environments is if you have a machine learning model that uses ML operations that are not supported by the standard runtime environment for LiteRT.

*   Flex runtime for LiteRT
*   Custom-built LiteRT runtime

The LiteRT Flex runtime lets you include specific operators required for your model. As an advanced option for running your model, you can build LiteRT for Android to include operators and other functionality required for running your TensorFlow machine learning model. For more information, see Build LiteRT for Android.

#### C and C++ APIs

LiteRT also provides an API for running models using C and C++. If your app uses the Android NDK, you should consider using this API. You may also want to consider using this API if you want to be able to share code between multiple platforms. For more information about this development option, see the Development tools page.

#### Server-based model execution

In general, you should run models in your app on an Android device to take advantage of lower latency and improved data privacy for your users. However, there are cases where running a model on a cloud server, off device, is a better solution. For example, if you have a large model which does not easily compress down to a size that fits on your users' Android devices, or can be executed with reasonable performance on those devices. This approach may also be your preferred solution if consistent performance of the model across a wide range of devices is top priority.

Google Cloud offers a full suite of services for running AI models. For more information, see Google Cloud's AI and machine learning products page.

#### Custom model development and optimization

More advanced development paths are likely to include developing custom machine learning models and optimizing those models for use on Android devices. If you plan to build custom models, make sure you consider applying quantization techniques to models to reduce memory and processing costs. For more information on how to build high-performance models for use with LiteRT, see Performance best practices in the Models section.

### Supported Android Versions

| LiteRT Version | Status | Min SDK Level | Min NDK Level (if used) | Release Date |
|---|---|---|---|---|
| v1.2.0 ⭐ | ✅ Active | 31 (Android 12 Snow Cone) | r26a | 2025-03-13 |
