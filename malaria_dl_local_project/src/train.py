import argparse

import tensorflow as tf

from src.config import OUTPUT_DIR
from src.data import load_malaria_splits
from src.metrics import evaluate_keras_model
from src.models import build_custom_cnn, build_vgg16_transfer, unfreeze_last_layers, compile_binary_model


def parse_args():
    parser = argparse.ArgumentParser(description="Entrenamiento local para NIH/NLM Malaria Dataset.")
    parser.add_argument("--model", choices=["custom_cnn", "vgg16"], required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--fine-tune-epochs", type=int, default=0)
    parser.add_argument("--img-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--no-augment", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    tf.keras.utils.set_random_seed(args.seed)

    output_dir = OUTPUT_DIR / args.model
    output_dir.mkdir(parents=True, exist_ok=True)

    ds_train, ds_val, ds_test, ds_info = load_malaria_splits(
        img_size=args.img_size,
        batch_size=args.batch_size,
        seed=args.seed,
        augment=not args.no_augment,
    )

    class_names = ds_info.features["label"].names
    print("Clases:", class_names)

    input_shape = (args.img_size, args.img_size, 3)

    if args.model == "custom_cnn":
        lr = args.learning_rate if args.learning_rate is not None else 1.0
        model = build_custom_cnn(input_shape=input_shape, learning_rate=lr)
        base_model = None
    else:
        lr = args.learning_rate if args.learning_rate is not None else 0.01
        model, base_model = build_vgg16_transfer(input_shape=input_shape, learning_rate=lr)

    model.summary()

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(output_dir / "best_model.keras"),
            monitor="val_accuracy",
            save_best_only=True,
            mode="max",
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=10,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(str(output_dir / "training_log.csv")),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=4,
            min_lr=1e-6,
            verbose=1,
        ),
    ]

    model.fit(
        ds_train,
        validation_data=ds_val,
        epochs=args.epochs,
        callbacks=callbacks,
    )

    if args.model == "vgg16" and args.fine_tune_epochs > 0:
        print("Iniciando fine-tuning parcial de VGG16...")
        unfreeze_last_layers(base_model, n_layers=4)
        model = compile_binary_model(
            model,
            learning_rate=0.001,
            optimizer_name="adadelta",
        )

        model.fit(
            ds_train,
            validation_data=ds_val,
            epochs=args.fine_tune_epochs,
            callbacks=callbacks,
        )

    print("Evaluación en test:")
    evaluate_keras_model(
        model=model,
        dataset=ds_test,
        class_names=class_names,
        output_dir=output_dir,
        prefix="test",
    )

    model.save(output_dir / "final_model.keras")
    print(f"Modelo final guardado en: {output_dir / 'final_model.keras'}")
    print(f"Mejor modelo guardado en: {output_dir / 'best_model.keras'}")


if __name__ == "__main__":
    main()
