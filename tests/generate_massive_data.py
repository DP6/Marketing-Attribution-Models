import argparse
import os
import time
import polars as pl
import numpy as np
import datetime


def generate_format_1_chunk(
    chunk_id: int, chunk_size: int, num_users: int
) -> pl.DataFrame:
    """Generates a memory-efficient chunk of Format 1 (Sessions) data."""
    channels = ["direct", "google_search", "meta_ads", "email", "organic_search"]

    # Generate random user IDs based on pool
    user_ids = np.random.randint(0, num_users, size=chunk_size)
    user_ids_str = [f"user_{uid}" for uid in user_ids]

    # Generate random datetimes within 2026-01-01 to 2026-01-31
    base_time = datetime.datetime(2026, 1, 1)
    seconds_offsets = np.random.randint(0, 30 * 24 * 3600, size=chunk_size)
    datetimes = [
        base_time + datetime.timedelta(seconds=int(offset))
        for offset in seconds_offsets
    ]

    # Generate channels
    channel_choices = np.random.choice(channels, size=chunk_size)

    # Generate conversions
    has_conversion = np.random.choice([True, False], size=chunk_size, p=[0.05, 0.95])

    return pl.DataFrame(
        {
            "datetime": datetimes,
            "user_id": user_ids_str,
            "channel": channel_choices,
            "has_conversion": has_conversion,
        }
    )


def main():
    parser = argparse.ArgumentParser(
        description="Gerador de Datasets Massivos para Nova MAM."
    )
    parser.add_argument(
        "--rows", type=int, default=100000, help="Número de linhas a gerar."
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=50000,
        help="Tamanho do chunk para salvar em disco.",
    )
    parser.add_argument(
        "--output-dir", type=str, default="data", help="Diretório de saída."
    )
    parser.add_argument(
        "--format",
        type=str,
        default="csv",
        choices=["csv", "parquet"],
        help="Formato de salvamento (csv ou parquet).",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Iniciando a geração de {args.rows:,} linhas...")
    start_time = time.time()

    num_users = max(1, args.rows // 4)
    chunks = (args.rows + args.chunk_size - 1) // args.chunk_size

    for i in range(chunks):
        this_chunk_size = min(args.chunk_size, args.rows - (i * args.chunk_size))
        chunk_df = generate_format_1_chunk(i, this_chunk_size, num_users)

        # Sort each chunk to keep the structure realistic
        chunk_df = chunk_df.sort(["user_id", "datetime"])

        if args.format == "csv":
            out_file = os.path.join(args.output_dir, f"format_1_chunk_{i}.csv")
            chunk_df.write_csv(out_file)
        else:
            out_file = os.path.join(args.output_dir, f"format_1_chunk_{i}.parquet")
            chunk_df.write_parquet(out_file)

        print(
            f"Chunk {i + 1}/{chunks} gerado e salvo em {out_file} ({this_chunk_size:,} linhas)"
        )

    duration = abs(time.time() - start_time)
    print(f"Geração concluída com sucesso em {duration:.2f} segundos!")


if __name__ == "__main__":
    main()
