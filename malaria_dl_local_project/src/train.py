import argparse
from pathlib import Path

import tensorflow as tf

from src.config import OUTPUT_DIR
from src.data import load_malaria_splits
from src.metrics import evaluate_keras_model
from src.models import build_custom_cnn, build_vgg16_transfer, unfreeze_last_layers, compile_binary_model
from src.preprocessing import PREPROCESSING_CHOICES, resolve_preprocessing_mode


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
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directorio de salida opcional. Si no se informa, usa "
            "outputs/<model> como antes."
        ),
    )
    parser.add_argument(
        "--preprocessing",
        choices=PREPROCESSING_CHOICES,
        default="auto",
        help=(
            "Modo de preprocesamiento. 'auto' mantiene compatibilidad con "
            "checkpoints existentes; usa vgg16_imagenet solo al reentrenar VGG16."
        ),
    )
    parser.add_argument(
        "--track-db",
        action="store_true",
        help="Registrar esta ejecución y sus resultados en PostgreSQL.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_context = None
    output_dir = (
        Path(args.output_dir).expanduser()
        if args.output_dir
        else OUTPUT_DIR / args.model
    )
    preprocessing_mode = resolve_preprocessing_mode(args.model, args.preprocessing)

    if args.track_db:
        from src.tracking_integration import (
            args_to_parameters,
            model_name_from_train_arg,
            start_tracking_run,
        )

        run_context = start_tracking_run(
            args=args,
            run_type="training",
            script_name="src.train",
            model_name=model_name_from_train_arg(args.model),
            run_name=f"train:{args.model}",
            parameters=args_to_parameters(
                args,
                extra={
                    "augment": not args.no_augment,
                    "checkpoint_dir": str(output_dir),
                    "output_dir": str(output_dir),
                    "preprocessing_mode": preprocessing_mode,
                },
            ),
            random_seed=args.seed,
        )

    try:
        tf.keras.utils.set_random_seed(args.seed)

        output_dir.mkdir(parents=True, exist_ok=True)

        ds_train, ds_val, ds_test, ds_info = load_malaria_splits(
            img_size=args.img_size,
            batch_size=args.batch_size,
            seed=args.seed,
            augment=not args.no_augment,
            preprocessing_mode=preprocessing_mode,
        )

        class_names = ds_info.features["label"].names
        print("Clases:", class_names)
        print("Preprocesamiento:", preprocessing_mode)

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

        history = model.fit(
            ds_train,
            validation_data=ds_val,
            epochs=args.epochs,
            callbacks=callbacks,
        )

        fine_tune_history = None
        if args.model == "vgg16" and args.fine_tune_epochs > 0:
            print("Iniciando fine-tuning parcial de VGG16...")
            unfreeze_last_layers(base_model, n_layers=4)
            model = compile_binary_model(
                model,
                learning_rate=0.001,
                optimizer_name="adadelta",
            )

            fine_tune_history = model.fit(
                ds_train,
                validation_data=ds_val,
                epochs=args.fine_tune_epochs,
                callbacks=callbacks,
            )

        print("Evaluación en test:")
        metrics = evaluate_keras_model(
            model=model,
            dataset=ds_test,
            class_names=class_names,
            output_dir=output_dir,
            prefix="test",
            threshold=0.5,
            metadata={"preprocessing_mode": preprocessing_mode},
        )

        model.save(output_dir / "final_model.keras")
        print(f"Modelo final guardado en: {output_dir / 'final_model.keras'}")
        print(f"Mejor modelo guardado en: {output_dir / 'best_model.keras'}")

        if args.track_db and run_context:
            from src.tracking_integration import (
                finish_tracking_run,
                log_metrics_and_reports,
                log_model_version,
                log_output_artifacts,
                log_training_history,
            )

            log_training_history(run_context, history, phase="training")
            if fine_tune_history is not None:
                log_training_history(
                    run_context,
                    fine_tune_history,
                    phase="fine_tuning",
                    epoch_offset=len(history.epoch),
                )
            log_metrics_and_reports(run_context, metrics, class_names, split_name="test")
            log_output_artifacts(run_context, output_dir)
            log_model_version(
                run_context,
                version_name=f"{args.model}_tracked",
                best_model_path=str(output_dir / "best_model.keras"),
                final_model_path=str(output_dir / "final_model.keras"),
            )
            finish_tracking_run(run_context, metadata={"status_detail": "training completed"})
    except Exception as exc:
        if args.track_db and run_context:
            from src.tracking_integration import fail_tracking_run

            fail_tracking_run(run_context, exc, script_name="src.train")
        raise


if __name__ == "__main__":
    main()
